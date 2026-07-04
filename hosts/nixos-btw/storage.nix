{ ... }:

{
  fileSystems."/mnt/backup-hdd" = {
    device = "/dev/disk/by-label/backup-hdd";
    fsType = "ext4";
    options = [
      "nofail"
      "x-systemd.device-timeout=10s"
    ];
  };
}
