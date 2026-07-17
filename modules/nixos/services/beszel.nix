{ ... }:

{
  services.beszel.hub = {
    enable = true;

    environment = {
      APP_URL = "http://monitor.home.arpa";
    };
  };
}
