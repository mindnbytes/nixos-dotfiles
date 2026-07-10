# Migrating Google Photos to Immich with `immich-go`

This document describes the process used to import a Google Photos library into Immich with [`immich-go`](https://github.com/simulot/immich-go).

The upstream documentation should remain the primary reference:

- [immich-go best practices](https://github.com/simulot/immich-go/blob/main/docs/best-practices.md)
- [immich-go installation and API key setup](https://github.com/simulot/immich-go/blob/main/docs/installation.md)

> [!IMPORTANT]
> Perform the migration separately for each Immich user. Each user should have their own Immich API key and Google Takeout archive.

## 1. Export Google Photos with Google Takeout

Open the Google Takeout export page:

<https://takeout.google.com/settings/takeout/custom/photos>

Recommended export settings:

- **Format:** ZIP
- **Archive size:** 50 GB, to minimize the number of parts
- **Content:** Include all photos, videos, albums, and associated metadata

After Google prepares the export, download every archive part completely.

Keep all Takeout ZIP files from the same export together in one directory. Do not extract or modify them before running `immich-go`.

Example:

```text
takeout-20260709T160532Z-2-001.zip
takeout-20260709T160532Z-2-002.zip
takeout-20260709T160532Z-2-003.zip
```

## 2. Create an Immich API key

Log in to Immich as the user whose library is being imported and create a dedicated API key.

Store the key in a local file that is:

- outside the Git repository;
- readable only by the current user;
- never committed to version control.

Example:

```bash
chmod 600 immich-alex-api.txt
```

Load the key into the current shell:

```bash
set -gx USER_API (string trim < immich-alex-api.txt)
```

This uses Fish shell syntax.

To remove it from the shell afterward:

```bash
set -e USER_API
```

## 3. Start a temporary shell with `immich-go`

Use the package from `nixos-unstable-small` without adding it permanently to the system configuration:

```bash
nix shell nixpkgs/nixos-unstable-small#immich-go
```

Confirm that it is available:

```bash
immich-go version
```

## 4. Run a dry run

Run the import first with `--dry-run`:

```bash
immich-go upload from-google-photos \
  --dry-run \
  --server=http://nixos-btw:2283 \
  --api-key="$USER_API" \
  --concurrent-tasks=8 \
  --client-timeout=60m \
  --pause-immich-jobs=true \
  --on-errors=continue \
  --manage-raw-jpeg=StackCoverRaw \
  --manage-burst=Stack \
  --manage-heic-jpeg=StackCoverJPG \
  takeout-20260709T160532Z-2-001.zip
```

When an export consists of multiple ZIP parts, verify the current `immich-go` documentation for the expected input pattern. Keep all parts from the export in the same directory.

### Relevant options

- `--dry-run`  
  Examines the archive and planned operations without uploading assets.

- `--server=http://nixos-btw:2283`  
  Address of the Immich server as reachable from the machine running `immich-go`.

- `--api-key="$USER_API"`  
  Uses the API key belonging to the target Immich user.

- `--concurrent-tasks=8`  
  Allows up to eight concurrent tasks. Reduce this if the server, network, or storage becomes overloaded.

- `--client-timeout=60m`  
  Allows long-running requests to complete.

- `--pause-immich-jobs=true`  
  Temporarily pauses normal Immich background jobs during the import, reducing competition for server resources.

- `--on-errors=continue`  
  Continues processing after individual errors. Review the final output and logs carefully.

- `--manage-raw-jpeg=StackCoverRaw`  
  Stacks matching RAW and JPEG files, using the RAW image as the stack cover.

- `--manage-burst=Stack`  
  Groups burst images into stacks.

- `--manage-heic-jpeg=StackCoverJPG`  
  Stacks matching HEIC and JPEG files, using the JPEG image as the stack cover.

## 5. Review the dry-run result

Before starting the real upload, check:

- whether the expected number of assets was detected;
- whether all Takeout parts were recognized;
- whether there are missing or unreadable files;
- whether duplicate handling looks reasonable;
- whether albums and timestamps are detected correctly;
- whether RAW/JPEG, HEIC/JPEG, and burst grouping behave as expected;
- whether the target Immich user is correct.

Resolve unexpected errors before proceeding.

## 6. Run the real import

Remove `--dry-run` and run the same command:

```bash
immich-go upload from-google-photos \
  --server=http://nixos-btw:2283 \
  --api-key="$USER_API" \
  --concurrent-tasks=8 \
  --client-timeout=60m \
  --pause-immich-jobs=true \
  --on-errors=continue \
  --manage-raw-jpeg=StackCoverRaw \
  --manage-burst=Stack \
  --manage-heic-jpeg=StackCoverJPG \
  takeout-20260709T160532Z-2-001.zip
```

For a long-running import over SSH, run it inside `tmux` or `screen`, or use another method that survives a disconnected SSH session.

Example with `tmux`:

```bash
tmux new -s immich-import
```

Run the import inside the session. Detach with `Ctrl-b`, then `d`.

Reattach later:

```bash
tmux attach -t immich-import
```

## 7. Validate the imported library

Do not delete or archive the Google Takeout files immediately after the command finishes.

First verify the imported library in Immich:

- check the overall asset count;
- inspect photos and videos from several different years;
- confirm that timestamps and time zones look correct;
- inspect albums;
- inspect burst stacks;
- inspect RAW/JPEG and HEIC/JPEG stacks;
- check Live Photos, if present;
- review failed or skipped files reported by `immich-go`;
- allow Immich background jobs to resume and finish;
- confirm that thumbnails, metadata extraction, search, and machine-learning jobs complete successfully.

Keep the original Takeout archive until the Immich library has also been included in a tested backup.

## 8. Archive the Google Takeout source

After validation, preserve the original Takeout ZIP files as an independent source archive.

Because the Takeout files are already ZIP-compressed, creating an uncompressed tar archive is usually sufficient and avoids spending CPU time attempting to compress them again:

```bash
tar -cf google-photos-takeout-20260709.tar takeout-*.zip
```

Move the archive to its long-term backup location:

```bash
mv google-photos-takeout-20260709.tar /secure-archive/
```

Optionally verify the archive before deleting the source files:

```bash
tar -tf /secure-archive/google-photos-takeout-20260709.tar >/dev/null
```

For stronger integrity checking, create a checksum:

```bash
sha256sum /secure-archive/google-photos-takeout-20260709.tar \
  > /secure-archive/google-photos-takeout-20260709.tar.sha256
```

Verify it:

```bash
sha256sum -c /secure-archive/google-photos-takeout-20260709.tar.sha256
```

> [!NOTE]
> Archiving the ZIP files into another tar file does not create an independent backup if both remain on the same physical disk. Keep at least one additional copy on separate storage.

## 9. Clean up temporary files

Only after successful validation and backup verification:

```bash
rm -rf /temp/immich-go-*
```

Delete the original Takeout ZIP files only when the archived copy has been verified and an independent backup exists:

```bash
rm -- takeout-*.zip
```

Remove the API key from the current shell:

```bash
set -e USER_API
```

Retain or delete the API key in Immich according to preference. A migration-specific key can be revoked after the import is complete.

## Per-user checklist

Repeat the following for each Immich account:

- [ ] Request and download the complete Google Takeout export
- [ ] Verify that all ZIP parts are present
- [ ] Create a dedicated Immich API key
- [ ] Store the key outside the repository with restrictive permissions
- [ ] Enter the temporary `nix shell`
- [ ] Run `immich-go` with `--dry-run`
- [ ] Review warnings, errors, asset counts, and stacking behavior
- [ ] Run the real import
- [ ] Review skipped and failed assets
- [ ] Validate the library in Immich
- [ ] Wait for Immich background jobs to finish
- [ ] Confirm that the Immich server is backed up
- [ ] Archive and checksum the original Takeout files
- [ ] Remove temporary files
- [ ] Revoke the migration API key, if no longer needed
