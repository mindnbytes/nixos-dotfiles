#!/usr/bin/env python3
"""Read-only, manually invoked health checks for the nixos-btw mini."""

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
import os
import platform
import subprocess
import sys


SERVICES = (
    "sshd", "postgresql", "redis-immich", "immich-server",
    "immich-machine-learning", "caddy", "beszel-hub", "beszel-agent",
)
FILESYSTEMS = (("/", None), ("/srv", "services"), ("/mnt/backup", "backup-hdd"))


class Unavailable(Exception):
    """The checker could not obtain reliable evidence."""


@dataclass
class Result:
    status: str
    check: str
    detail: str


def run(command, timeout=10, allowed=(0,)):
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "LC_ALL": "C"},
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise Unavailable(f"{command[0]}: {error}") from error
    if allowed is not None and result.returncode not in allowed:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise Unavailable(f"{command[0]} exited {result.returncode}: {detail}")
    return result


def check_service(name):
    output = run([
        "systemctl", "show", f"{name}.service", "--no-pager",
        "--property=LoadState,ActiveState,SubState",
    ]).stdout
    properties = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
    if not all(key in properties for key in ("LoadState", "ActiveState", "SubState")):
        raise Unavailable("systemctl returned incomplete service state")
    load, active, sub = (properties[key] for key in ("LoadState", "ActiveState", "SubState"))
    healthy = load == "loaded" and active == "active" and sub == "running"
    return Result("PASS" if healthy else "FAIL", f"service/{name}",
                  f"{load}, {active}/{sub}")


def check_immich():
    # Numeric loopback avoids a dependency on the mini's own home.arpa resolver.
    # The Host header selects the configured Caddy virtual host.
    response = run([
        "curl", "--disable", "--silent", "--show-error", "--noproxy", "*",
        "--connect-timeout", "3", "--max-time", "8",
        "--header", "Host: immich.home.arpa", "--write-out", "\n%{http_code}",
        "http://127.0.0.1/api/server/ping",
    ], allowed=None)
    if response.returncode:
        return Result("FAIL", "http/immich", response.stderr.strip() or "HTTP request failed")
    body, separator, status = response.stdout.rpartition("\n")
    if not separator or status != "200":
        return Result("FAIL", "http/immich", f"expected HTTP 200; received {status or 'no status'}")
    try:
        healthy = json.loads(body) == {"res": "pong"}
    except ValueError:
        healthy = False
    return Result("PASS" if healthy else "FAIL", "http/immich",
                  "Caddy → Immich returned pong" if healthy else "HTTP 200 with unexpected response")


def check_storage(path, label, min_free_percent):
    # Access in a subprocess: a missing backup disk must not block the checker.
    # The backup automount is configured with a 60-second device timeout.
    stats = run(["stat", "--file-system", "--format=%a %b %S", path],
                timeout=70 if path == "/mnt/backup" else 10).stdout
    mount_result = run([
        "findmnt", "--json", "--list", "--mountpoint", path,
        "--output", "TARGET,SOURCE,FSTYPE,OPTIONS",
    ], allowed=(0, 1))
    if mount_result.returncode == 1:
        return Result("FAIL", f"storage/{path}", "expected filesystem is not mounted here")
    try:
        mounts = json.loads(mount_result.stdout)["filesystems"]
        # An automount and its actual filesystem may both appear for one target.
        mounts = [mount for mount in mounts if mount["fstype"] != "autofs"]
        if len(mounts) != 1:
            raise ValueError("expected exactly one mounted filesystem")
        mount = mounts[0]
        source, fstype = mount["source"], mount["fstype"]
        options = mount["options"].split(",")
        available, total, block_size = map(int, stats.split())
        if total <= 0 or available < 0 or block_size <= 0:
            raise ValueError("invalid filesystem capacity")
    except (ValueError, KeyError, TypeError) as error:
        raise Unavailable(f"cannot interpret filesystem information: {error}") from error
    if label:
        # Resolve the expected label independently; a directory on / is not enough.
        expected = run(["readlink", "--canonicalize-existing", f"/dev/disk/by-label/{label}"]).stdout.strip()
        actual = run(["readlink", "--canonicalize-existing", source]).stdout.strip()
        if actual != expected:
            return Result("FAIL", f"storage/{path}", f"{source}; expected disk labeled {label}")
    if fstype != "ext4" or "rw" not in options:
        return Result("FAIL", f"storage/{path}", f"{source}: expected writable ext4, got {fstype} ({','.join(options)})")
    free_percent = available / total * 100
    free_gib = available * block_size / 1024**3
    status = "PASS" if free_percent >= min_free_percent else "WARN"
    return Result(status, f"storage/{path}",
                  f"{source}; {free_percent:.1f}% free ({free_gib:.1f} GiB); threshold {min_free_percent:g}%")


def check_failed_units():
    output = run([
        "systemctl", "--failed", "--no-legend", "--plain", "--no-pager",
    ]).stdout
    units = [line.split()[0] for line in output.splitlines() if line.strip()]
    return Result("FAIL" if units else "PASS", "os/failed-units",
                  ", ".join(units) if units else "no failed systemd units")


def collect(min_free_percent):
    checks = [(f"service/{name}", lambda name=name: check_service(name)) for name in SERVICES]
    checks.append(("http/immich", check_immich))
    checks.extend((f"storage/{path}", lambda path=path, label=label:
                   check_storage(path, label, min_free_percent)) for path, label in FILESYSTEMS)
    checks.append(("os/failed-units", check_failed_units))
    results = []
    for name, check in checks:
        try:
            results.append(check())
        except Unavailable as error:
            results.append(Result("UNKNOWN", name, str(error)))
    return results


def percentage(value):
    number = float(value)
    if not math.isfinite(number) or not 0 < number < 100:
        raise argparse.ArgumentTypeError("must be greater than 0 and less than 100")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print a structured report")
    parser.add_argument("--min-free-percent", type=percentage, default=15,
                        help="warn below this available-space percentage (default: 15)")
    args = parser.parse_args()
    if platform.system() != "Linux":
        parser.exit(2, "mini-health must run on the Linux mini, not the MacBook.\n")
    results = collect(args.min_free_percent)
    healthy = all(result.status == "PASS" for result in results)
    if args.json:
        print(json.dumps({
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "hostname": platform.node(), "healthy": healthy,
            "results": [asdict(result) for result in results],
        }, indent=2))
    else:
        for result in results:
            print(f"{result.status:7} {result.check:32} {result.detail}")
        print(f"\n{sum(result.status == 'PASS' for result in results)}/{len(results)} checks passed")
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())
