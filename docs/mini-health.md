# Mini server health check

## Installed command and schedule

`hosts/nixos-btw/health.nix` packages the checker and its command dependencies
from the pinned Nixpkgs input. After activating the configuration on the mini:

```sh
sudo mini-health
sudo mini-health --json
systemctl list-timers mini-health.timer
journalctl -u mini-health.service -n 50 --no-pager
```

The system service runs as Alex, with journal-reading access and supplementary
`immich` group access to the media tree, at **ten minutes
past every hour** in the mini's local timezone. This gives the scheduled Borg
jobs time to finish. The persistent timer runs once after activation or boot
if a scheduled run was missed while the timer was inactive. It does not replay
every missed hour. Each service invocation has an overall ten-minute timeout.

The checker exits nonzero for any `WARN`, `FAIL`, or `UNKNOWN`; systemd records
that invocation as failed, with the report in the journal. The timer continues
to schedule subsequent checks. Optional Healthchecks reporting is described
below; no automatic repairs are set up.

For an immediate run with the service's exact environment and permissions:

```sh
sudo systemctl start mini-health.service
journalctl -u mini-health.service -n 50 --no-pager
```

Starting a system service uses sudo; the checker itself runs as Alex and does
not use sudo. A direct run needs access to both the journal and Immich's dump
directory; without it, the affected checks report `UNKNOWN`. Use `sudo
mini-health` for a direct run if the invoking account lacks access.

Deploy the module using the normal procedure from the mini's checkout:

```sh
sudo nixos-rebuild switch --flake .#nixos-btw
```

## Optional Healthchecks heartbeat and email

The scheduled service runs a reporting wrapper around the checker. It sends an
empty HTTPS POST only when **all checks pass**. It never sends failure signals,
logs, check names, or other diagnostic content. Manual `mini-health` runs do not
send anything. The provider can observe the request time and public source IP.
No incoming connection or router port forwarding is needed.

### Configure the hosted check

On Healthchecks.io, create one check with a generic name such as `Home server`:

1. Choose a simple schedule with a **one-hour period** and **one-hour grace**.
2. Enable email notifications for the down and recovery transitions. Disable
   repeated reminders and periodic reports if you want only those messages.
3. Keep the UUID success-ping URL private. Use the normal
   `https://hc-ping.com/UUID` URL, without `/fail`, `/start`, or query parameters.

Healthy hourly runs keep it quiet. Unhealthy runs send nothing. About two hours
without a success signal triggers an email; a later passing run sends the
heartbeat and triggers recovery. An isolated unhealthy run may produce no email
if the next run succeeds in time. Power loss, network trouble, and a stopped
checker all appear as missing heartbeats.

### Install the credential on the mini

After rebuilding, the module provides `/var/lib/mini-health` as a root-only
directory. For **initial setup only**, create a root-only file, then edit it to
contain the success-ping URL on one line:

```sh
sudo install -m 600 -o root -g root /dev/null /var/lib/mini-health/healthchecks-url
sudoedit /var/lib/mini-health/healthchecks-url
```

Do not run the `install` command over an existing credential: it empties the
file. For later changes, use `sudoedit` only. Do not put the URL in Git, a Nix
string, a command argument, shell history, or a pasted journal report.

Systemd reads that file as root and delivers it to the Alex-owned service using
`LoadCredential`. Its contents are outside the Nix store and the generated unit.
A non-secret `disabled` default in `SetCredential` lets local checks continue when the
source file is absent or cannot be loaded; the journal then says reporting is
not configured. An unreadable runtime credential or an invalid URL fails the
reporting invocation without disclosing the value. No rebuild is needed to
change the URL: credentials are loaded on each service start.

The reporter accepts the hosted UUID URL only, disables redirects and ambient
HTTP proxies, and makes at most two attempts with a five-second socket timeout
and a one-second pause. TLS uses the packaged CA certificates. Delivery failure
is logged without the URL and makes the service fail; subsequent hourly runs
still execute. Continued missing heartbeats are detected by Healthchecks.

### Verify

```sh
sudo systemctl start mini-health.service
journalctl -u mini-health.service -n 50 --no-pager
```

Confirm both the local report and `Healthchecks heartbeat sent.`, then confirm
receipt in the hosted dashboard. Verify problem/recovery email delivery using
a separate temporary hosted check with short timings. Pause the hosted check
before deliberately disabling reporting for maintenance.

No local notification state, counters, mail server, or detailed remote report
is required. Future checks automatically affect whether the heartbeat is sent.

## Run from source

Run `scripts/mini-health.py` **on the Linux mini**, with access to the journal
and dump directory. It checks:

- Running SSH, PostgreSQL, Redis, Immich server and machine learning, Caddy,
  Beszel hub, and Beszel agent services.
- An HTTP 200 response with `{"res":"pong"}` from Immich through Caddy.
- Writable ext4 filesystems at `/`, `/srv`, and `/mnt/backup`, with the expected
  disk labels for the latter two and at least 15% available space on each.
- Failed systemd units, including failed backup or maintenance units.
- For both Borg jobs: an enabled, active timer with a next run; the result of
  the last job invocation; and the age of the latest successful backup recorded
  in the journal with a Borg archive summary.
- The modification time of the newest nonempty `*.sql.gz` Immich database dump
  in `/srv/immich/media/backups`, with a default freshness limit of 36 hours.

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
sudo python3 scripts/mini-health.py
sudo python3 scripts/mini-health.py --json
sudo python3 scripts/mini-health.py --min-free-percent 20
sudo python3 scripts/mini-health.py --max-backup-age-hours 48
sudo python3 scripts/mini-health.py --max-dump-age-hours 48
```

Dependencies: Python 3.9 or newer, `systemctl`, `journalctl`, `curl`, `findmnt`,
GNU `find`, and GNU `stat`/`readlink`. No third-party Python packages are required.
The scheduled service has the groups needed to read the journal and dump directory;
direct runs need equivalent access. Unavailable evidence reports `UNKNOWN` and
the other checks still run.

If Python or curl is missing, use the repository's pinned packages for a
temporary environment (this may download packages):

```sh
nix shell --no-write-lock-file --inputs-from . nixpkgs#python3 nixpkgs#curl --command sh -c 'exec sudo env PATH="$PATH" python3 scripts/mini-health.py'
```

For a check from the MacBook, after deploying the packaged checker on the mini:

```sh
ssh -t mini 'sudo mini-health'
```

## Interpret results

- `PASS`: the check obtained the expected evidence.
- `WARN`: disk space is low, the latest successful backup is stale, or a backup
  is still running, or the newest Immich database dump is stale.
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

If systemd has no completed-run record, for example after reboot, the run-result
check uses the latest completed attempt in the retained journal. A structured
failure event counts even if Borg failed before writing an archive summary.
An older success never hides a newer failure. Current systemd failure or
running state takes precedence; no reboot grace period is needed. Missing or
incomplete journal evidence remains `UNKNOWN`. Run result and freshness share
one journal read per job.

Freshness still uses the latest qualifying success, independently of the
latest attempt's outcome. It means a backup job completed successfully recently; it
does not inspect whether the archive is still on disk, its contents, or
database-dump freshness.

### Other checks

The dump check reads only file names, sizes, and modification times. An
accessible directory with no nonempty matching dumps fails; a missing or
inaccessible directory or a timestamp more
than five minutes in the future is `UNKNOWN`. It does not validate dump contents,
completion, compatibility, or whether the dump is present in a Borg archive.
The check does not start, stop, or gate the Borg job. Change the dump age limit
if the Immich dump schedule is longer than the default daily schedule.

The HTTP probe connects to loopback with the `immich.home.arpa` Host header, so
it tests Caddy routing and the Immich ping endpoint. It does not test client
DNS, LAN access, login, media retrieval, database queries, or ML inference.
Beszel checks currently verify running services, not fresh metrics or its UI.

Expected units and disk labels match the host declarations in
`hosts/nixos-btw/`; keep them aligned when changing that configuration. A failed
unit can reflect a past failure and needs investigation; it does not always
mean the application is currently unavailable. Filesystem checks are snapshots,
not disk integrity tests.

Archive contents, kernel/OOM history, and SMART are later steps. A passing report does not establish backup
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
They also cover journal fallback when runtime records are missing, failures
before an archive summary, and one shared journal read per job.
Reporter tests cover success-only gating, disabled/empty/missing/invalid credentials,
secret redaction, delivery failure, retries, empty HTTP bodies, and redirect
rejection. HTTP contract tests use a loopback server and never contact the
hosted service.
