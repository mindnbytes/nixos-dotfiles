#!/usr/bin/env python3
"""Run the local checker and send a success-only Healthchecks heartbeat."""

import os
import http.client
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


def valid_ping_url(url):
    try:
        parsed = urllib.parse.urlsplit(url)
        identifier = parsed.path.removeprefix("/")
        return (parsed.scheme == "https" and parsed.netloc == "hc-ping.com"
                and not parsed.query and not parsed.fragment
                and str(uuid.UUID(identifier)) == identifier)
    except ValueError:
        return False


def send_heartbeat(url):
    # Do not follow redirects, use ambient proxy settings, or pass the private
    # URL in process arguments. Exceptions must never be printed: they contain it.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    for attempt in range(2):
        try:
            request = urllib.request.Request(url, data=b"", method="POST",
                                             headers={"User-Agent": "mini-health"})
            with opener.open(request, timeout=5) as response:
                if response.status == 200:
                    return True
        except (OSError, urllib.error.URLError, http.client.HTTPException, ValueError):
            pass
        if attempt == 0:
            time.sleep(1)
    return False


def run_and_report(checker):
    try:
        result = subprocess.run([checker], check=False)
    except OSError:
        print("Heartbeat withheld: could not start the health checker.", flush=True)
        return 2
    if result.returncode != 0:
        print("Heartbeat withheld: health checks did not all pass.", flush=True)
        return result.returncode if result.returncode > 0 else 128 - result.returncode

    directory = os.environ.get("CREDENTIALS_DIRECTORY")
    if not directory:
        print("Heartbeat not configured; local checks only.", flush=True)
        return 0
    try:
        url = (Path(directory) / "healthchecks-url").read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        print("Heartbeat configuration could not be read.", flush=True)
        return 1
    if url in ("", "disabled"):
        print("Heartbeat not configured; local checks only.", flush=True)
        return 0
    if not valid_ping_url(url):
        print("Heartbeat configuration invalid: expected a hosted Healthchecks UUID ping URL.", flush=True)
        return 1
    if not send_heartbeat(url):
        print("Heartbeat delivery failed after two attempts; details suppressed to protect the URL.", flush=True)
        return 1
    print("Healthchecks heartbeat sent.", flush=True)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: mini-health-report.py CHECKER")
    sys.exit(run_and_report(sys.argv[1]))
