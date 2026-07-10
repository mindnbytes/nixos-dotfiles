# Borg Backup Job Checklist

This note documents the practical workflow around Borg jobs on the mini server: what to do before declaring a job, what to put in the NixOS job declaration, and what to do after the job exists.

The intended layout is:

```text
/mnt/backup
  borg-mini-home
  borg-mini-immich
  borg-mini-some-other-service
```

with `/mnt/backup` being the external USB HDD mounted by NixOS.

---

## 1. Before creating a Borg job

### 1.1 Verify that the backup disk is mounted

```bash
findmnt /mnt/backup
df -h /mnt/backup
ls -la /mnt/backup
```

Expected:

```text
/mnt/backup /dev/sdX1 ext4 ...
```

If `x-systemd.automount` is used, `findmnt /mnt/backup` may show both:

```text
/mnt/backup systemd-1 autofs ...
/mnt/backup /dev/sdX1 ext4 ...
```

That is okay. The `autofs` line is the systemd automount trigger, and the `ext4` line is the real mounted disk.

### 1.2 Ensure the mount is declared

In the mini host storage module, for example `hosts/nixos-btw/storage.nix`:

```nix
{ ... }:

{
  fileSystems."/mnt/backup" = {
    device = "/dev/disk/by-label/backup-hdd";
    fsType = "ext4";
    options = [
      "nofail"
      "x-systemd.automount"
      "x-systemd.device-timeout=60s"
    ];
  };
}
```

Why:

- `nofail` means the mini can boot even if the backup disk is disconnected.
- `x-systemd.automount` means the disk is mounted when `/mnt/backup` is accessed.
- `x-systemd.device-timeout=60s` gives the USB HDD/enclosure time to appear.

### 1.3 Create a passphrase file outside Git and outside the Nix store

Do not put Borg passphrases directly into Nix with `passphrase = "..."`.

Create root-only passphrase files manually:

```bash
nix shell nixpkgs#openssl
sudo install -d -m 700 /var/lib/borg-secrets

openssl rand -base64 32 | sudo tee /var/lib/borg-secrets/mini-home.passphrase >/dev/null
openssl rand -base64 32 | sudo tee /var/lib/borg-secrets/mini-immich.passphrase >/dev/null

sudo fish -c "chmod 600 /var/lib/borg-secrets/*.passphrase"
sudo fish -c "chown root:root /var/lib/borg-secrets/*.passphrase"
```

Later, store these passphrases in KeePassXC/Bitwarden as well.

---

## 2. Recommended job structure

Use separate jobs and separate repos:

```text
mini-home:
  personal/home important files

mini-immich:
  server/application data
```

This keeps failure modes separate. A failed database dump should not necessarily affect a simple home-file backup.

---

## 3. Example Borg NixOS module

Example file:

```text
hosts/mini/backup.nix
```

or:

```text
modules/nixos/backup/borg.nix
```

Example contents:

```nix
{ ... }:

let
  commonCompression = "auto,zstd,3";

  commonKeep = {
    daily = 7;
    weekly = 4;
    monthly = 6;
  };

  commonExclude = [
    "**/.cache"
    "**/node_modules"
    "**/target"
    "**/build"
    "**/dist"
    "**/.Trash-*"
  ];
in
{
  services.borgbackup.jobs = {
    mini-home = {
      paths = [
        "/home/alex/Documents"
        "/home/alex/nixos-dotfiles"

        # Add later if needed:
        # "/home/alex/Pictures"
        # "/home/alex/.ssh"
      ];

      exclude = commonExclude ++ [
        "/home/alex/Downloads"
      ];

      repo = "/mnt/backup/borg-mini-home";
      removableDevice = true;
      doInit = false;

      encryption = {
        mode = "repokey-blake2";
        passCommand = "cat /var/lib/borg-secrets/mini-home.passphrase";
      };

      compression = commonCompression;
      archiveBaseName = "mini-home";
      prune.keep = commonKeep;

      extraCreateArgs = [
        "--stats"
        "--checkpoint-interval" "600"
      ];

      # Keep timers disabled while testing manually.
      startAt = [ ];
    };

    mini-immich = {
      paths = [
        "/srv/immich/media"
      ];

      exclude = commonExclude ++ [
        "/srv/**/tmp"
      ];

      repo = "/mnt/backup/borg-mini-immich";
      removableDevice = true;
      doInit = false;

      encryption = {
        mode = "repokey-blake2";
        passCommand = "cat /var/lib/borg-secrets/mini-immich.passphrase";
      };

      compression = commonCompression;
      archiveBaseName = "mini-immich";
      prune.keep = commonKeep;

      extraCreateArgs = [
        "--stats"
        "--checkpoint-interval" "600"
      ];

      # Keep timers disabled while testing manually.
      startAt = [ ];
    };
  };

  systemd.services.borgbackup-job-mini-home.unitConfig.RequiresMountsFor = [
    "/mnt/backup"
  ];

  systemd.services.borgbackup-job-mini-immich.unitConfig.RequiresMountsFor = [
    "/mnt/backup"
  ];
}
```

### Why these options

#### `repo`

```nix
repo = "/mnt/backup/borg-mini-home";
```

The Borg repository location.

#### `removableDevice = true`

Use this for a USB/external backup disk. It helps avoid creating repo directories on the root filesystem when the external disk is not mounted.

#### `doInit = false`

For real repos, initialize manually once. This makes mistakes fail loudly instead of silently creating a fresh empty repo.

Use `doInit = true` only for dummy/test jobs.

#### `encryption.mode = "repokey-blake2"`

Good default for local encrypted Borg repos.

#### `passCommand`

Keeps the secret outside the Nix store.

#### `prune.keep`

Example:

```nix
prune.keep = {
  daily = 7;
  weekly = 4;
  monthly = 6;
};
```

This roughly means:

```text
keep one daily archive for 7 days
keep one weekly archive for 4 weeks
keep one monthly archive for 6 months
```

It does not mean “keep 7 backups from today.”

#### `startAt = [ ]`

Disables automatic timers while testing.

Later replace with real schedules.

#### `RequiresMountsFor = [ "/mnt/backup" ]`

Makes the Borg service require the backup disk mount. If `/mnt/backup` cannot be mounted, the Borg job should fail instead of writing to the wrong place.

---

## 4. After declaring the job

### 4.1 Rebuild

```bash
sudo nixos-rebuild switch
```

Check wrappers:

```bash
which borg-job-mini-home
which borg-job-mini-immich
```

### 4.2 Initialize repos manually

Make sure the disk is mounted:

```bash
findmnt /mnt/backup
ls /mnt/backup
```

Initialize:

```bash
sudo borg-job-mini-home init --encryption=repokey-blake2
sudo borg-job-mini-immich init --encryption=repokey-blake2
```

Check:

```bash
sudo borg-job-mini-home info
sudo borg-job-mini-immich info
```

### 4.3 Run first backups manually

Use the systemd services for actual configured backup runs:

```bash
sudo systemctl start borgbackup-job-mini-home.service
sudo systemctl start borgbackup-job-mini-immich.service
```

Check status:

```bash
systemctl status borgbackup-job-mini-home.service
systemctl status borgbackup-job-mini-immich.service
```

Check logs:

```bash
journalctl -u borgbackup-job-mini-home.service -n 100 --no-pager
journalctl -u borgbackup-job-mini-immich.service -n 100 --no-pager
```

List archives:

```bash
sudo borg-job-mini-home list
sudo borg-job-mini-immich list
```

Important distinction:

```text
systemctl start borgbackup-job-NAME.service
  runs the configured backup job

borg-job-NAME list/info/check/extract/init
  runs Borg maintenance commands against that repo
```

---

## 5. Export Borg keys

For encrypted repositories, export the Borg key and store it safely.

```bash
sudo borg-job-mini-home key export /root/borg-mini-home-key.txt
sudo borg-job-mini-immich key export /root/borg-mini-immich-key.txt
```

Then copy the key contents and passphrases into a safe place, such as KeePassXC or Bitwarden.

For recovery, you need:

```text
Borg repository
+
Borg passphrase
+
preferably exported Borg key backup
```

After storing key exports elsewhere, decide whether to remove the `/root/borg-*-key.txt` files.

---

## 6. Test restore

Backups are not real until restore works.

### 6.1 List archives

```bash
sudo borg-job-mini-home list
```

Pick an archive name.

### 6.2 Restore to a temporary directory

```bash
sudo mkdir -p /tmp/borg-restore-home
cd /tmp/borg-restore-home
sudo borg-job-mini-home extract --dry-run ::ARCHIVE_NAME
sudo borg-job-mini-home extract ::ARCHIVE_NAME
```

Inspect:

```bash
find /tmp/borg-restore-home -maxdepth 5 -type f | head -50
ls -la /tmp/borg-restore-home
```

Do the same for server:

```bash
sudo borg-job-mini-immich list

sudo mkdir -p /tmp/borg-restore-immich
cd /tmp/borg-restore-immich
sudo borg-job-mini-immich extract --dry-run ::ARCHIVE_NAME
sudo borg-job-mini-immich extract ::ARCHIVE_NAME

find /tmp/borg-restore-immich -maxdepth 5 -type f | head -50
```

### 6.3 Restoring files back to their real locations

Borg stores ownership and permissions. To preserve them, restore as root and copy with metadata-preserving tools.

Good:

```bash
sudo rsync -aHAX /tmp/borg-restore-home/home/alex/Documents/ /home/alex/Documents/
```

For simple files, this is often enough:

```bash
sudo rsync -a /tmp/borg-restore-home/home/alex/Documents/ /home/alex/Documents/
```

Also acceptable:

```bash
sudo cp -a source destination
```

Avoid plain `cp` for real restores because it can lose metadata.

---

## 7. Check repository health

After first successful backups:

```bash
sudo borg-job-mini-home check --repository-only
sudo borg-job-mini-immich check --repository-only
```

Later, run checks occasionally.

---

## 8. Enable automatic timers later

Only after manual backup and restore work.

Change:

```nix
startAt = [ ];
```

to staggered schedules, for example:

```nix
# mini-home
startAt = "*-*-* 02:00:00";
persistentTimer = true;
inhibitsSleep = true;
```

```nix
# mini-immich
startAt = "*-*-* 03:00:00";
persistentTimer = true;
inhibitsSleep = true;
```

Then rebuild:

```bash
sudo nixos-rebuild switch
```

Check timers:

```bash
systemctl list-timers | grep borg
```

---

## 9. Routine commands

Manual run:

```bash
sudo systemctl start borgbackup-job-mini-home.service
sudo systemctl start borgbackup-job-mini-immich.service
```

Logs:

```bash
journalctl -u borgbackup-job-mini-home.service -n 100 --no-pager
journalctl -u borgbackup-job-mini-immich.service -n 100 --no-pager
```

List archives:

```bash
sudo borg-job-mini-home list
sudo borg-job-mini-immich list
```

Repo info:

```bash
sudo borg-job-mini-home info
sudo borg-job-mini-immich info
```

Check repo:

```bash
sudo borg-job-mini-home check --repository-only
sudo borg-job-mini-immich check --repository-only
```

Check mount:

```bash
findmnt /mnt/backup
df -h /mnt/backup
```

---

## 10. Quick checklist for adding a new job

Before:

```text
[ ] Backup destination exists and is mounted.
[ ] Passphrase file exists outside Git/Nix store.
[ ] Source paths exist.
[ ] Excludes are reasonable.
[ ] Repo path is correct.
```

In Nix:

```text
[ ] Separate repo for the job.
[ ] removableDevice = true for USB/local removable disk.
[ ] doInit = false for real jobs.
[ ] encryption uses repokey-blake2.
[ ] passCommand points to root-only passphrase file.
[ ] prune.keep is set.
[ ] startAt = [ ] while testing.
[ ] RequiresMountsFor includes /mnt/backup.
```

After:

```text
[ ] nixos-rebuild switch.
[ ] borg-job-NAME init --encryption=repokey-blake2.
[ ] systemctl start borgbackup-job-NAME.service.
[ ] borg-job-NAME list shows archive.
[ ] Borg key exported and stored safely.
[ ] Restore test completed.
[ ] Timer enabled only after restore test works.
```

---

## 11. Philosophy

For real backups, prefer:

```text
fail loudly > silently create a new repo
restore test > successful backup command
explicit source paths > backing up everything
separate home/immich jobs > one huge complicated job
local Borg backup now > perfect off-site system never
```
