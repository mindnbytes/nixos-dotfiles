# Immich v3 migration follow-up

- [ ] Protect Immich and Beszel client traffic with HTTPS using Caddy's local certificate authority; install and trust its root certificate on clients.
- [ ] Review Borg exclusions for Immich separately from home-directory exclusions, and verify representative media paths are archived.
- [ ] Review database dump and media consistency during backups, validate dump recoverability and archive contents, and test a full restore. The health check monitors dump freshness but does not guarantee a usable or consistent backup.
