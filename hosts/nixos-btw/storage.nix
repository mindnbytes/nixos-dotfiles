{ ... }:

{
  fileSystems."/mnt/backup" = {
    device = "/dev/disk/by-label/backup-hdd";
    fsType = "ext4";
    options = [
      "nofail"
      "x-systemd.automount"
      "x-systemd.device-timeout=60s"
    ];
  };
}
