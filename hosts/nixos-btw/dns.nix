{ ... }:

{
  services.dnsmasq = {
    enable = true;
    # Keep mini's own resolver unchanged while the LAN DNS is being tested.
    resolveLocalQueries = false;
    settings = {
      interface = "enp1s0f0";
      bind-dynamic = true;
      local-service = true;
      no-resolv = true;
      server = [ "9.9.9.9" "149.112.112.112" ];
      local = "/home.arpa/";
      host-record = [
        "immich.home.arpa,192.168.2.76"
        "monitor.home.arpa,192.168.2.76"
      ];
    };
  };

  networking.firewall.interfaces.enp1s0f0 = {
    allowedTCPPorts = [ 53 ];
    allowedUDPPorts = [ 53 ];
  };
}
