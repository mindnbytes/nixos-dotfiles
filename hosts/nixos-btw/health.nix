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
      findutils
    ];
    text = ''
      exec python3 ${../../scripts/mini-health.py} "$@"
    '';
  };
  reporter = pkgs.writeShellApplication {
    name = "mini-health-report";
    runtimeInputs = [ pkgs.python3 ];
    text = ''
      export SSL_CERT_FILE=${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt
      exec python3 ${../../scripts/mini-health-report.py} ${checker}/bin/mini-health
    '';
  };
in
{
  environment.systemPackages = [ checker ];
  systemd.tmpfiles.rules = [ "d /var/lib/mini-health 0700 root root - -" ];

  systemd.services.mini-health = {
    description = "Check mini server health";
    wants = [ "network-online.target" ];
    after = [ "network-online.target" ];

    serviceConfig = {
      Type = "oneshot";
      User = "alex";
      SupplementaryGroups = [ "systemd-journal" "immich" ];
      ExecStart = "${reporter}/bin/mini-health-report";
      LoadCredential = [ "healthchecks-url:/var/lib/mini-health/healthchecks-url" ];
      # A non-secret default keeps local checks working before setup.
      # A configured LoadCredential value takes precedence over this default.
      SetCredential = [ "healthchecks-url:disabled" ];
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
