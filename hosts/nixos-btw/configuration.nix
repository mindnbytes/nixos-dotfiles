{
  config,
  lib,
  pkgs,
  ...
}:

{
  imports = [
    ./hardware-configuration.nix
    ./storage.nix
    ./immich.nix
    ../../modules/nixos/backup/borg.nix
    ../../modules/nixos/services/caddy.nix
  ];

  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  networking.hostName = "nixos-btw"; # Define your hostname.

  networking.networkmanager.enable = true;

  nixpkgs.config.allowUnfreePredicate =
    pkg:
    builtins.elem (lib.getName pkg) [
      "b43-firmware"
    ];
  networking.enableB43Firmware = true;

  time.timeZone = "Europe/Berlin";

  services.gnome.gcr-ssh-agent.enable = false;
  services.gnome.gnome-keyring.enable = true;
  services.displayManager.ly.enable = true;
  services.xserver = {
    enable = true;
    autoRepeatDelay = 200;
    autoRepeatInterval = 35;
    windowManager.qtile.enable = true;
  };

  security.pam.services.login.enableGnomeKeyring = true;

  users.users.alex = {
    isNormalUser = true;
    extraGroups = [ "wheel" ]; # Enable ‘sudo’ for the user.
    shell = pkgs.fish;
    openssh.authorizedKeys.keys = [
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAEBc+D/LqeB3835KXSM5J/dSU1nPwiszC5pPcGpykoi macbook-to-nixos-mini"
    ];
  };

  programs.firefox.enable = true;
  programs.fish.enable = true;
  programs.ssh.startAgent = true;

  services.openssh = {
    enable = true;
    openFirewall = true;

    settings = {
      PasswordAuthentication = false;
      KbdInteractiveAuthentication = false;
      PermitRootLogin = "no";

      AllowUsers = [ "alex" ];
    };
  };

  # List packages installed in system profile.
  environment.systemPackages = with pkgs; [
    vim
    wget
    git
    smartmontools
  ];

  fonts.packages = with pkgs; [
    nerd-fonts.jetbrains-mono
  ];

  nix.settings.experimental-features = [
    "nix-command"
    "flakes"
  ];

  nix.gc = {
    automatic = true;
    dates = "daily";
    options = "--delete-older-than 10d";
  };

  nix.optimise = {
    automatic = true;
    dates = [ "weekly" ];
  };

  system.stateVersion = "26.05";

}
