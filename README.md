# NixOS and Home Manager dotfiles

Personal configuration for two machines:

| Target | Machine | Manages |
| --- | --- | --- |
| `nixos-btw` | 2012 Intel Mac mini running NixOS | OS, Immich, Caddy, DNS, Beszel, Borg backups, and Alex's Home Manager profile |
| `alex-macbook` | Apple Silicon MacBook | Standalone Home Manager packages and dotfiles |

## Everyday use

Keep the checkout at `~/nixos-dotfiles`: `/home/alex/nixos-dotfiles` on the mini and `/Users/alex/nixos-dotfiles` on the MacBook.

On the mini, apply both system and home configuration:

```sh
cd ~/nixos-dotfiles
sudo nixos-rebuild switch --flake .#nixos-btw
```

On the MacBook, apply home configuration:

```sh
cd ~/nixos-dotfiles
home-manager switch --flake .#alex-macbook
```

These commands use the versions pinned in `flake.lock`. Most packages use stable Nixpkgs; selected applications use unstable. Updating inputs is a separate action: `nix flake update`. Review the lock-file change before rebuilding.

Git and SSH configs link to the live checkout. Edits to those files do not require a rebuild, though the application may need reloading. Keep the checkout in place; Home Manager rollback does not undo those edits.

## Where things live

- `flake.nix`: inputs and the two configuration targets.
- `hosts/nixos-btw/`: server hardware, storage, users, Immich, Borg, Caddy, DNS, and Beszel.
- `home/`: shared packages, shell/editor settings, and machine profiles.
- `config/`: application dotfiles linked into the home directory.
- `docs/`: installation and recovery procedures.

## Server prerequisites

- ext4 disk labeled `services`, mounted at `/srv`; ext4 disk labeled `backup-hdd`, automounted at `/mnt/backup`.
- Root-only files created outside Git: `/var/lib/borg-secrets/mini-home.passphrase`, `/var/lib/borg-secrets/mini-immich.passphrase`, and `/var/lib/secrets/beszel-agent.env`.
- Borg repositories initialized once using the checklist below; recovery uses the existing repositories.
- Speedport DHCP reservation and NetworkManager IPv6 address for the mini's DNS service; see the DNS runbook.

For a fresh install, follow the runbook: it includes setting Alex's sudo password and copying the installation checkout into the home directory. SSH access is key-only.

## Runbooks

- [Nix editor completion](docs/nix-editor-completion.md): dotfiles defaults and project-specific overrides for Helix.
- [Immich server operations](docs/immich-server-operations.md): deployment, backup, restore, and fresh installation.
- [Home DNS](docs/home-dns.md): dnsmasq, Speedport settings, testing, and recovery.
- [Borg backup checklist](docs/borg-backup-job-checklist.md): secrets, repository initialization, and restore checks.
- [Beszel setup](docs/beszel-setup-notes.md): hub account, agent authorization, and monitoring.
- [Health check](docs/mini-health.md): hourly checks, optional success-only Healthchecks/email reporting, and manual `mini-health` use.
- [Google Photos migration](docs/immich-google-photos-migration.md): importing Takeout with `immich-go`.
