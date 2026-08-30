# Immich Server Operations

This runbook covers deployment, backup, restore, and fresh installation for the `nixos-btw` Immich server.

## System layout

| Item | Value |
| --- | --- |
| NixOS flake target | `.#nixos-btw` |
| Immich URL | `http://immich.home.arpa` |
| Direct Immich address | `http://nixos-btw:2283` |
| Service filesystem | ext4 filesystem labeled `services`, mounted at `/srv` |
| Immich media | `/srv/immich/media` |
| Immich database dumps | `/srv/immich/media/backups` |
| PostgreSQL data | `/srv/postgresql` |
| Backup filesystem | ext4 filesystem labeled `backup-hdd`, automounted at `/mnt/backup` |
| Borg repository | `/mnt/backup/borg-mini-immich` |
| Borg passphrase | `/var/lib/borg-secrets/mini-immich.passphrase` |
| Borg schedule | Daily at `03:00`; missed runs execute after the next boot |
| Borg retention | 7 daily, 4 weekly, and 6 monthly archives |

Immich creates database dumps inside its media directory. Borg backs up the complete media directory, including those dumps. A usable recovery requires both the media files and a compatible database dump from the same Borg archive.

## Deploy or update

Run these commands from the repository root on `nixos-btw`.

1. Verify the service filesystem:

   ```bash
   findmnt /srv
   findmnt --noheadings --output SOURCE,FSTYPE /srv
   ```

   The source must be the ext4 filesystem labeled `services`. Do not deploy or start Immich with `/srv` unmounted.

2. Build and activate the configuration:

   ```bash
   sudo nixos-rebuild switch --flake .#nixos-btw
   ```

3. Verify the services and timer:

   ```bash
   systemctl --no-pager --full status postgresql.service
   systemctl --no-pager --full status immich-server.service
   systemctl --no-pager --full status immich-machine-learning.service
   systemctl --no-pager --full status caddy.service
   systemctl list-timers borgbackup-job-mini-immich.timer
   ```

4. Open `http://immich.home.arpa` and confirm that the library loads.

For a failed deployment, inspect:

```bash
journalctl -u postgresql.service -u immich-server.service \
  -u immich-machine-learning.service -u caddy.service \
  -b --no-pager
```

## Back up

### Automatic backup

Immich stores automatic database dumps in:

```text
/srv/immich/media/backups
```

The dump schedule and retention are controlled in **Administration → Settings → Backup**. Immich defaults to a daily dump at `02:00` and retention of 14 dumps.

At `03:00`, `borgbackup-job-mini-immich.service` archives `/srv/immich/media` to `/mnt/backup/borg-mini-immich`. The backup disk is mounted on access.

Check recent database dumps and Borg runs:

```bash
sudo find /srv/immich/media/backups -maxdepth 1 -type f -name '*.sql.gz' -ls
sudo borg-job-mini-immich list
journalctl -u borgbackup-job-mini-immich.service -n 100 --no-pager
```

### Manual backup

1. In Immich, open **Administration → Job Queues**.
2. Click **Create job**, select **Create Database Dump**, and confirm.
3. Confirm that a new dump exists:

   ```bash
   sudo find /srv/immich/media/backups -maxdepth 1 -type f -name '*.sql.gz' -ls
   ```

4. Run Borg:

   ```bash
   sudo systemctl start borgbackup-job-mini-immich.service
   systemctl --no-pager --full status borgbackup-job-mini-immich.service
   sudo borg-job-mini-immich list
   ```

5. Inspect the new archive and confirm that it contains media and `srv/immich/media/backups`:

   ```bash
   sudo borg-job-mini-immich list ::ARCHIVE_NAME
   ```

Replace `ARCHIVE_NAME` with the archive name printed by the repository listing.

Periodically check repository integrity:

```bash
sudo borg-job-mini-immich check --repository-only
```

Recovery requires the Borg repository and its passphrase. Keep a separate copy of the passphrase and exported Borg key outside the server.

## Restore

This procedure replaces the current media tree and database with one archived state.

1. Mount the backup disk and select an archive:

   ```bash
   findmnt /mnt/backup
   sudo borg-job-mini-immich list
   ```

2. Extract the archive into an empty directory:

   ```bash
   sudo mkdir -p /var/tmp/immich-restore
   cd /var/tmp/immich-restore
   sudo borg-job-mini-immich extract --dry-run ::ARCHIVE_NAME
   sudo borg-job-mini-immich extract ::ARCHIVE_NAME
   ```

3. Confirm that the extraction contains the media tree and at least one database dump:

   ```bash
   sudo find /var/tmp/immich-restore/srv/immich/media/backups \
     -maxdepth 1 -type f -name '*.sql.gz' -ls
   ```

4. Stop Immich:

   ```bash
   sudo systemctl stop immich-server.service immich-machine-learning.service
   ```

5. Preserve the current media tree and install the extracted tree:

   ```bash
   sudo mv /srv/immich/media /srv/immich/media.before-restore
   sudo cp -a /var/tmp/immich-restore/srv/immich/media /srv/immich/media
   sudo chown -R immich:immich /srv/immich/media
   ```

   Ensure `/srv` has enough free space for both copies before running these commands.

6. Start Immich:

   ```bash
   sudo systemctl start immich-machine-learning.service immich-server.service
   ```

7. Log in as an Immich administrator. Open **Administration → Maintenance → Restore database backup**, select the database dump from the restored media tree, and confirm the restore. Select the newest compatible dump created before the Borg archive.

8. Verify the restored system:

   ```bash
   systemctl --no-pager --full status postgresql.service immich-server.service
   journalctl -u postgresql.service -u immich-server.service -n 100 --no-pager
   ```

   Check users, albums, asset count, and representative photos and videos in the web interface.

9. After verification, remove the temporary extraction and the previous media tree:

   ```bash
   sudo rm -rf /var/tmp/immich-restore
   sudo rm -rf /srv/immich/media.before-restore
   ```

Do not copy archived PostgreSQL data files over a running `/srv/postgresql` directory.

## Fresh installation

The repository does not declare OS disk partitioning. Before this procedure, provision the target OS disk and mount its root filesystem at `/mnt` and EFI system partition at `/mnt/boot`. Do not format the `services` or `backup-hdd` filesystems when recovering their existing contents.

1. Make the configuration repository available at:

   ```text
   /mnt/etc/nixos/nixos-dotfiles
   ```

2. Generate hardware configuration for the target machine:

   ```bash
   sudo nixos-generate-config --root /mnt
   sudo cp /mnt/etc/nixos/hardware-configuration.nix \
     /mnt/etc/nixos/nixos-dotfiles/hosts/nixos-btw/hardware-configuration.nix
   ```

3. Connect the ext4 filesystems labeled `services` and `backup-hdd`, then verify their labels:

   ```bash
   lsblk --fs
   ```

4. Install the host configuration:

   ```bash
   sudo nixos-install --flake /mnt/etc/nixos/nixos-dotfiles#nixos-btw
   sudo reboot
   ```

5. Restore the Borg passphrase from its separate secret copy:

   ```bash
   sudo install -d -m 700 -o root -g root /var/lib/borg-secrets
   sudo install -m 600 -o root -g root /PATH/TO/mini-immich.passphrase \
     /var/lib/borg-secrets/mini-immich.passphrase
   ```

6. Confirm access to the existing repository:

   ```bash
   findmnt /mnt/backup
   sudo borg-job-mini-immich info
   sudo borg-job-mini-immich list
   ```

   Do not run `borg init` when recovering the existing repository.

7. Recover Immich:

   - If the `services` filesystem still contains `/srv/immich/media` and `/srv/postgresql`, start the system normally and verify Immich.
   - If the `services` filesystem is blank or replaced, restore the Borg archive through step 6 of the restore procedure. Open the Immich welcome screen, choose **Restore from backup**, select a dump from `/srv/immich/media/backups`, and complete onboarding.

8. Verify the deployment and run one manual backup using the backup procedure above.
