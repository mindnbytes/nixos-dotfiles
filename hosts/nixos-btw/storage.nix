{ ... }:
let
  commonFsType = "ext4";
  commonOptions = [
    "nofail"
    "x-systemd.automount"
    "x-systemd.device-timeout=60s"
  ];
in
{
  fileSystems = {
    "/mnt/backup" = {
      device = "/dev/disk/by-label/backup-hdd";
      fsType = commonFsType;
      options = commonOptions;
    };
    "/srv" = {
      device = "/dev/disk/by-label/services";
      fsType = commonFsType;
      options = commonOptions;
    };
  };
}
