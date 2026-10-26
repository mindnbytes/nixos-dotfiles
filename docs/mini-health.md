# Mini server health check

## Installed command and schedule

`hosts/nixos-btw/health.nix` packages the checker and its command dependencies
from the pinned Nixpkgs input. After activating the configuration on the mini:

```sh
mini-health
mini-health --json
systemctl list-timers mini-health.timer
journalctl -u mini-health.service -n 50 --no-pager
```

The system service runs as Alex, with journal-reading access, at **ten minutes
past every hour** in the mini's local timezone. This gives the scheduled Borg
jobs time to finish. The persistent timer runs once after activation or boot
if a scheduled run was missed while the timer was inactive. It does not replay
every missed hour. Each service invocation has an overall ten-minute timeout.

The checker exits nonzero for any `WARN`, `FAIL`, or `UNKNOWN`; systemd records
that invocation as failed, with the report in the journal. The timer continues
to schedule subsequent checks. No notifications or automatic repairs are set up.

For an immediate run with the service's exact environment and permissions:

```sh
sudo systemctl start mini-health.service
journalctl -u mini-health.service -n 50 --no-pager
```

Starting a system service uses sudo; the checker itself runs as Alex and does
not use sudo. `mini-health` can be run directly without elevated privileges.

Deploy the module using the normal procedure from the mini's checkout:

```sh
sudo nixos-rebuild switch --flake .#nixos-btw
```

## Run from source

Run `scripts/mini-health.py` **on the Linux mini**. It checks:

- Running SSH, PostgreSQL, Redis, Immich server and machine learning, Caddy,
  Beszel hub, and Beszel agent services.
- An HTTP 200 response with `{"res":"pong"}` from Immich through Caddy.
- Writable ext4 filesystems at `/`, `/srv`, and `/mnt/backup`, with the expected
  disk labels for the latter two and at least 15% available space on each.
- Failed systemd units, including failed backup or maintenance units.
- For both Borg jobs: an enabled, active timer with a next run; the result of
  the last job invocation; and the age of the latest successful backup recorded
  in the journal with a Borg archive summary.

The script queries state without restarting services or running backups. It
does not invoke Borg or sudo. Accessing `/mnt/backup` triggers its configured
automount and may wake the disk. That check allows 70 seconds for the configured
60-second device wait; other commands time out after 10 seconds, and HTTP after
8 seconds. Checks run
sequentially and continue when a command fails or times out.

## Run

From the mini's checkout:

```sh
cd /home/alex/nixos-dotfiles
python3 scripts/mini-health.py
python3 scripts/mini-health.py --json
python3 scripts/mini-health.py --min-free-percent 20
python3 scripts/mini-health.py --max-backup-age-hours 48
```

Dependencies: Python 3.9 or newer, `systemctl`, `journalctl`, `curl`, `findmnt`,
and GNU `stat`/`readlink`. No third-party Python packages or root privileges are
required. Alex can read both jobs' journals on the mini. If journal access is
unavailable, freshness reports `UNKNOWN` and the other checks still run.

If Python or curl is missing, use the repository's pinned packages for a
temporary environment (this may download packages):

```sh
nix shell --no-write-lock-file --inputs-from . nixpkgs#python3 nixpkgs#curl --command python3 scripts/mini-health.py
```

For a check from the MacBook, after the script is present in the mini's checkout:

```sh
ssh mini 'cd /home/alex/nixos-dotfiles && nix shell --no-write-lock-file --inputs-from . nixpkgs#python3 nixpkgs#curl --command python3 scripts/mini-health.py'
```

## Interpret results

- `PASS`: the check obtained the expected evidence.
- `WARN`: disk space is low, the latest successful backup is stale, or a backup
  is still running.
- `FAIL`: observed state differs from the expected state.
- `UNKNOWN`: the check could not obtain evidence, for example because a command
  is missing, a disk access timed out, or permissions prevented inspection.

Exit status is `0` only when every check passes, `1` for any other health result,
and `2` for invalid arguments or execution on a non-Linux system. JSON includes
the report timestamp in UTC, hostname, aggregate `healthy` flag, and individual
results. Nothing is stored automatically.

For service failures, use `systemctl status UNIT` and
`journalctl -b -u UNIT --no-pager`. For storage failures, inspect `lsblk --fs`,
`findmnt`, and the kernel journal before changing anything.

## Scope and limits

### Backup freshness

The daily schedules are `15:00` for `mini-home` and `03:00` for `mini-immich`,
in the mini's local timezone. The default freshness limit is **36 hours**.
`journalctl` supplies JSON entries from the last seven days, with a longer
lookback of the configured limit plus 24 hours when needed. There is no fixed
line limit, and records from previous boots are included when retained.

A qualifying run needs a Borg `Archive name:` matching the job, a `Time (end):`
summary line, and systemd's structured successful-deactivation event from PID 1.
Both sides must identify the same service invocation, and the summary must
precede completion. The freshness timestamp comes from the journal's precise
completion timestamp, so no local date strings need parsing. The `.failed`
suffix printed during creation is temporary: the NixOS wrapper removes it
after successful creation. The suffix alone does not determine the result.

Timer, last-run result, and freshness are separate report lines. A recent
success does not hide a disabled timer or a failed latest job. A running job is
`WARN` until it completes. Missing readable success evidence, incomplete or
malformed records, or a success timestamp more than five minutes in the future
produce `UNKNOWN`. A qualifying success older than the limit produces `WARN`.

Systemd may have no previous run recorded after a reboot, in which case the
run-result check is `UNKNOWN`; retained journal evidence can still establish
freshness. Freshness means a backup job completed successfully recently; it
does not inspect whether the archive is still on disk, its contents, or
database-dump freshness.

### Other checks

The HTTP probe connects to loopback with the `immich.home.arpa` Host header, so
it tests Caddy routing and the Immich ping endpoint. It does not test client
DNS, LAN access, login, media retrieval, database queries, or ML inference.
Beszel checks currently verify running services, not fresh metrics or its UI.

Expected units and disk labels match the host declarations in
`hosts/nixos-btw/`; keep them aligned when changing that configuration. A failed
unit can reflect a past failure and needs investigation; it does not always
mean the application is currently unavailable. Filesystem checks are snapshots,
not disk integrity tests.

Archive contents, kernel/OOM history, SMART, and
notifications are later steps. A passing report does not establish backup
recoverability or detect a server that is powered off.

## Local verification

Failure-path tests mock commands and never contact the mini:

```sh
python3 -m unittest discover -s tests -v
```

They cover inactive/missing services, HTTP failures and unexpected responses,
wrong or missing mounts, automount handling, low space, read-only filesystems,
missing commands, timeouts, and continuing after an unavailable check.
Backup tests cover disabled timers, unsuccessful and running jobs, fresh/stale
success events, the exact age threshold, invocation matching, later failed runs,
missing summaries, malformed/future timestamps, and unavailable journal access.
