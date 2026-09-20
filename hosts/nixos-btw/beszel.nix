{ ... }:

{
  services.beszel = {
    hub = {
      enable = true;

      environment = {
        APP_URL = "http://monitor.home.arpa";
      };
    };
    agent = {
      enable = true;

      environment = {
        LISTEN = "127.0.0.1:45876";
        SYSTEM_NAME = "nixos-btw";
      };

      environmentFile = "/var/lib/secrets/beszel-agent.env";
    };
  };
}
