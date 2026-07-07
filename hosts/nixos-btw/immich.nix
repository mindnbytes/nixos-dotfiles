{ ... }:

{
  # Make sure the directories exist with correct ownwership.
  systemd.tmpfiles.rules = [
    "d /srv/immich/media 0750 immich immich - -"
    "d /srv/postgresql 0700 postgres postgres - -"
  ];

  services.postgresql = {
    enable = true;
    dataDir = "/srv/postgresql";
  };

  services.immich = {
    enable = true;

    # Local network access
    host = "0.0.0.0";
    port = 2283;
    openFirewall = true;

    # One the USB NVMe SSD
    mediaLocation = "/srv/immich/media";

    # Keep enabled initially; it is local.
    machine-learning.enable = true;

    # Optional: less noisy logs
    environment.IMMICH_LOG_LEVEL = "warn";
  };

  # Optional, reduces Redis log noise.
  services.redis.servers.immich.logLevel = "warning";

  # Prevent services from starting if /srv is not mounted.
  systemd.services.postgresql.unitConfig.requiresMountsFor = [ "/srv"];
  systemd.services.immich-server.unitConfig.requiresMountsFor = [ "/srv"];
  systemd.services.immich-machine-learning.unitConfig.requiresMountsFor = "/srv";
}
