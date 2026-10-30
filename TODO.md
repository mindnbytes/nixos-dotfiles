# Immich v3 migration follow-up

- [ ] Protect Immich and Beszel client traffic with HTTPS using Caddy's local certificate authority; install and trust its root certificate on clients.
- [ ] Verify representative Immich media paths are archived after separating Borg exclusions.
- [ ] Review database dump and media consistency during backups and archive contents. The health check monitors dump freshness but does not guarantee a usable or consistent backup; restoration has not been tested.
