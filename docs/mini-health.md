# Manual mini server health check

Run `scripts/mini-health.py` **on the Linux mini**. This first version checks:

- Running SSH, PostgreSQL, Redis, Immich server and machine learning, Caddy,
  Beszel hub, and Beszel agent services.
- An HTTP 200 response with `{"res":"pong"}` from Immich through Caddy.
- Writable ext4 filesystems at `/`, `/srv`, and `/mnt/backup`, with the expected
  disk labels for the latter two and at least 15% available space on each.
- Failed systemd units, including failed backup or maintenance units.

The script queries state without restarting services, writing data, or running
backups. Accessing `/mnt/backup` triggers its configured automount and may wake
the disk. That check allows 70 seconds for the configured 60-second device wait;
other commands time out after 10 seconds, and HTTP after 8 seconds. Checks run
sequentially and continue when a command fails or times out.

## Run

From the mini's checkout:

```sh
cd /home/alex/nixos-dotfiles
python3 scripts/mini-health.py
python3 scripts/mini-health.py --json
python3 scripts/mini-health.py --min-free-percent 20
```

Dependencies: Python 3.9 or newer, `systemctl`, `curl`, `findmnt`, and GNU
`stat`/`readlink`. No third-party Python packages or root privileges are required.
If Python or curl is missing, use the repository's pinned packages for a
temporary environment (this may download packages):

```sh
nix shell --inputs-from . nixpkgs#python3 nixpkgs#curl --command python3 scripts/mini-health.py
```

For a check from the MacBook, after the script is present in the mini's checkout:

```sh
ssh mini 'cd /home/alex/nixos-dotfiles && python3 scripts/mini-health.py'
```

## Interpret results

- `PASS`: the check obtained the expected evidence.
- `WARN`: available disk space is below the configured threshold.
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

The HTTP probe connects to loopback with the `immich.home.arpa` Host header, so
it tests Caddy routing and the Immich ping endpoint. It does not test client
DNS, LAN access, login, media retrieval, database queries, or ML inference.
Beszel checks currently verify running services, not fresh metrics or its UI.

Expected units and disk labels match the host declarations in
`hosts/nixos-btw/`; keep them aligned when changing that configuration. A failed
unit can reflect a past failure and needs investigation; it does not always
mean the application is currently unavailable. Filesystem checks are snapshots,
not disk integrity tests.

Backup freshness, archive contents, kernel/OOM history, SMART, scheduling, and
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
