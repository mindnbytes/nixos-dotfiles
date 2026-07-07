{ ... }:
let
  commonFsType = "ext4";
in
{
  fileSystems = {
    "/mnt/backup" = {
      device = "/dev/disk/by-label/backup-hdd";
      fsType = commonFsType;
      options = [
        "nofail"
        "x-systemd.automount"
        "x-systemd.device-timeout=60s"
      ];
    };
    "/srv" = {
      device = "/dev/disk/by-label/services";
      fsType = commonFsType;
      options = [
        "x-systemd.device-timeout=60s"
      ];
    };
  };
}
