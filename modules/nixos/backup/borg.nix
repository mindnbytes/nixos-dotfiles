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
        "/home/alex/Projects"
        "/home/alex/nixos-dotfiles"
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
        "--checkpoint-interval"
        "600"
      ];

      startAt = "*-*-* 15:00:00";
      persistentTimer = true;
      inhibitsSleep = true;
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
        "--checkpoint-interval"
        "600"
      ];

      startAt = "*-*-* 03:00:00";
      persistentTimer = true;
      inhibitsSleep = true;
    };
  };
  # Optional explicit guard. The Borg module already adds RequiresMountsFor
  # for local repos, but keeping this explicit is readable.
  systemd.services.borgbackup-job-mini-home.unitConfig.RequiresMountsFor = [
    "/mnt/backup"
  ];

  systemd.services.borgbackup-job-mini-immich.unitConfig.RequiresMountsFor = [
    "/mnt/backup"
  ];
}
