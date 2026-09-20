{ ... }:

{
  services.caddy = {
    enable = true;

    virtualHosts = {
      "http://immich.home.arpa".extraConfig = ''
        reverse_proxy 127.0.0.1:2283
      '';

      "http://monitor.home.arpa".extraConfig = ''
        request_body {
          max_size 10MB
        }

        reverse_proxy 127.0.0.1:8090 {
          transport http {
            read_timeout 360s
          }
        }
      '';
    };
  };
  networking.firewall.allowedTCPPorts = [ 80 ];
}
