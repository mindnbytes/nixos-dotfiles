{ pkgs, ... }:

let
  checker = pkgs.writeShellApplication {
    name = "mini-health";
    runtimeInputs = with pkgs; [
      python3
      systemd
      util-linux
      coreutils
      curl
    ];
    text = ''
      exec python3 ${../../scripts/mini-health.py} "$@"
    '';
  };
in
{
  environment.systemPackages = [ checker ];

  systemd.services.mini-health = {
    description = "Check mini server health";
    wants = [ "network-online.target" ];
    after = [ "network-online.target" ];

    serviceConfig = {
      Type = "oneshot";
      User = "alex";
      SupplementaryGroups = [ "systemd-journal" ];
      ExecStart = "${checker}/bin/mini-health";
      TimeoutStartSec = "10min";
      NoNewPrivileges = true;
      StandardOutput = "journal";
      StandardError = "journal";
    };
  };

  systemd.timers.mini-health = {
    description = "Run mini server health checks hourly";
    wantedBy = [ "timers.target" ];
    timerConfig = {
      # Let the 03:00 and 15:00 backup jobs finish before checking them.
      OnCalendar = "*-*-* *:10:00";
      Persistent = true;
    };
  };
}
