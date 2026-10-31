{ ... }:

{
  services.tailscale.enable = true;

  services.rex.loginServer = {
    enable = true;
    tailscaleServe.enable = true;

    accounts.alex.principals = [ "tailscale:mindnbytes@gmail.com" ];
  };
}
