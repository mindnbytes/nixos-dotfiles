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
BACKUP_JOBS = ("mini-home", "mini-immich")
# systemd's structured UNIT_SUCCESS event, verified against the mini's journal.
UNIT_SUCCESS = "7ad2d189f7e94e70a38c781354912448"
UNIT_FAILURES = {"d9b373ed55a64feb8242e02dbe79a49c", "be02cf6855d2428ba40df7e9d022f03d"}


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
            stdin=subprocess.DEVNULL, env={**os.environ, "LC_ALL": "C.UTF-8"},
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


def backup_properties(unit, names):
    output = run([
        "systemctl", "show", unit, "--no-pager", "--property=" + ",".join(names),
    ]).stdout
    properties = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
    if not all(name in properties for name in names):
        raise Unavailable("systemctl returned incomplete backup state")
    return properties


def check_backup_timer(job):
    state = backup_properties(f"borgbackup-job-{job}.timer", (
        "LoadState", "ActiveState", "UnitFileState", "NextElapseUSecRealtime",
    ))
    healthy = (state["LoadState"] == "loaded" and state["ActiveState"] == "active"
               and state["UnitFileState"] == "enabled"
               and state["NextElapseUSecRealtime"] not in ("", "n/a"))
    detail = (f"{state['LoadState']}, {state['ActiveState']}, {state['UnitFileState']}; "
              f"next: {state['NextElapseUSecRealtime'] or 'not scheduled'}")
    return Result("PASS" if healthy else "FAIL", f"backup/{job}/timer", detail)


def check_backup_run(job, history=None, now=None):
    state = backup_properties(f"borgbackup-job-{job}.service", (
        "LoadState", "ActiveState", "Result", "ExecMainStatus", "ExecMainExitTimestamp",
    ))
    name = f"backup/{job}/run"
    if state["LoadState"] != "loaded":
        return Result("FAIL", name, f"service {state['LoadState']}")
    if state["ActiveState"] in ("activating", "active", "deactivating"):
        return Result("WARN", name, "backup is in progress; current run has not completed")
    if state["ActiveState"] == "failed" or state["Result"] != "success" or state["ExecMainStatus"] != "0":
        return Result("FAIL", name, f"last run: {state['Result']}, exit {state['ExecMainStatus']}")
    if not state["ExecMainExitTimestamp"]:
        evidence = history() if history else read_backup_history(job)
        latest = evidence["latest_attempt"]
        if latest is None:
            raise Unavailable("no completed backup attempt in the readable journal")
        timestamp, status = latest
        completed = datetime.fromtimestamp(timestamp, timezone.utc)
        if (completed - (now or datetime.now(timezone.utc))).total_seconds() > 300:
            raise Unavailable("latest backup attempt is in the future; check the system clock")
        if status == "UNKNOWN":
            raise Unavailable("latest completed journal attempt has no matching Borg summary")
        outcome = "succeeded" if status == "PASS" else "failed"
        return Result(status, name, f"last completed attempt {outcome}: {completed.isoformat()} (journal)")
    return Result("PASS", name, f"last run succeeded: {state['ExecMainExitTimestamp']}")


def read_backup_history(job, max_age_hours=36):
    unit = f"borgbackup-job-{job}.service"
    lookback_hours = max(168, max_age_hours + 24)
    output = run([
        "journalctl", "--unit", unit, "--since", f"{lookback_hours:.0f} hours ago",
        "--output=json", "--no-pager", "--quiet",
    ]).stdout
    summaries, completions = {}, []
    try:
        for line in output.splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            timestamp = int(entry["__REALTIME_TIMESTAMP"]) / 1_000_000
            if not math.isfinite(timestamp) or timestamp <= 0:
                raise ValueError("invalid journal timestamp")
            datetime.fromtimestamp(timestamp, timezone.utc)
            message = entry.get("MESSAGE", "")
            invocation = entry.get("_SYSTEMD_INVOCATION_ID")
            if invocation and entry.get("_SYSTEMD_UNIT") == unit and isinstance(message, str):
                summary = summaries.setdefault(invocation, {})
                if message.startswith(f"Archive name: {job}-") and ".checkpoint" not in message:
                    summary["archive"] = message.removeprefix("Archive name: ").strip()
                    summary["archive_time"] = timestamp
                if message.startswith("Time (end):"):
                    summary["end_time"] = timestamp
            # PID 1 logs use INVOCATION_ID, whereas Borg's own log records use
            # _SYSTEMD_INVOCATION_ID. Never pair messages from different runs.
            event = entry.get("MESSAGE_ID")
            if (entry.get("_PID") == "1" and entry.get("UNIT") == unit
                    and (event == UNIT_SUCCESS or event in UNIT_FAILURES)):
                completions.append((timestamp, entry.get("INVOCATION_ID"), event))
        attempts, successes = [], []
        for timestamp, invocation, event in completions:
            summary = summaries.get(invocation, {})
            qualified = ({"archive", "archive_time", "end_time"} <= summary.keys()
                         and max(summary["archive_time"], summary["end_time"]) <= timestamp)
            if event in UNIT_FAILURES:
                status = "FAIL"
            elif qualified:
                status = "PASS"
                successes.append(timestamp)
            else:
                status = "UNKNOWN"
            attempts.append((timestamp, status))
        return {
            "latest_attempt": max(attempts, key=lambda attempt: (attempt[0], attempt[1] == "FAIL"), default=None),
            "latest_success": max(successes, default=None),
            "lookback_hours": lookback_hours,
        }
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError, OSError) as error:
        raise Unavailable(f"cannot interpret backup journal: {error}") from error


def check_backup_freshness(job, max_age_hours, now=None, history=None):
    evidence = history() if history else read_backup_history(job, max_age_hours)
    if evidence["latest_success"] is None:
        raise Unavailable(f"no successful backup with a Borg summary in the last {evidence['lookback_hours']:g}h of readable journal")
    completed = datetime.fromtimestamp(evidence["latest_success"], timezone.utc)
    age_hours = ((now or datetime.now(timezone.utc)) - completed).total_seconds() / 3600
    if age_hours < -5 / 60:
        raise Unavailable("successful backup timestamp is in the future; check the system clock")
    status = "PASS" if age_hours <= max_age_hours else "WARN"
    return Result(status, f"backup/{job}/freshness",
                  f"successful backup completed {completed.isoformat()}; age {max(0, age_hours):.1f}h; limit {max_age_hours:g}h (journal)")


def collect(min_free_percent, max_backup_age_hours=36):
    histories = {}

    def history(job):
        # Share evidence, including read failures, between the two checks.
        if job not in histories:
            try:
                histories[job] = read_backup_history(job, max_backup_age_hours)
            except Unavailable as error:
                histories[job] = error
        if isinstance(histories[job], Unavailable):
            raise histories[job]
        return histories[job]

    checks = [(f"service/{name}", lambda name=name: check_service(name)) for name in SERVICES]
    checks.append(("http/immich", check_immich))
    checks.extend((f"storage/{path}", lambda path=path, label=label:
                   check_storage(path, label, min_free_percent)) for path, label in FILESYSTEMS)
    checks.append(("os/failed-units", check_failed_units))
    for job in BACKUP_JOBS:
        checks.extend([
            (f"backup/{job}/timer", lambda job=job: check_backup_timer(job)),
            (f"backup/{job}/run", lambda job=job: check_backup_run(job, history=lambda: history(job))),
            (f"backup/{job}/freshness", lambda job=job:
             check_backup_freshness(job, max_backup_age_hours, history=lambda: history(job))),
        ])
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


def positive_hours(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite number greater than 0")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print a structured report")
    parser.add_argument("--min-free-percent", type=percentage, default=15,
                        help="warn below this available-space percentage (default: 15)")
    parser.add_argument("--max-backup-age-hours", type=positive_hours, default=36,
                        help="warn when the latest successful backup is older than this (default: 36)")
    args = parser.parse_args()
    if platform.system() != "Linux":
        parser.exit(2, "mini-health must run on the Linux mini, not the MacBook.\n")
    results = collect(args.min_free_percent, args.max_backup_age_hours)
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
