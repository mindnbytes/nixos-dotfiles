{ pkgsUnstable, ... }:

{
  # Make sure the directories exist with correct ownership.
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
    package = pkgsUnstable.immich;

    # Expose Immich through Caddy only.
    host = "127.0.0.1";
    port = 2283;
    openFirewall = false;

    # On the USB NVMe SSD
    mediaLocation = "/srv/immich/media";

    # Keep enabled initially; it is local.
    machine-learning.enable = true;

    # Include the database backup success message used by mini-health.
    environment.IMMICH_LOG_LEVEL = "log";
  };

  # Optional, reduces Redis log noise.
  services.redis.servers.immich.logLevel = "warning";

  # Prevent services from starting if /srv is not mounted.
  systemd.services.postgresql.unitConfig.RequiresMountsFor = [ "/srv" ];
  systemd.services.immich-server.unitConfig.RequiresMountsFor = [ "/srv" ];
  systemd.services.immich-machine-learning.unitConfig.RequiresMountsFor = "/srv";
}
