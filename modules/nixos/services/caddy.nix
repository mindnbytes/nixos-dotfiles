{ ... }:

{
  services.caddy = {
    enable = true;

    virtualHosts = {
      "http://immich.home.arpa" = {
        extraConfig = ''
          reverse_proxy 127.0.0.1:2283
        '';
      };
    };
  };
  networking.firewall.allowedTCPPorts = [ 80 ];
}
