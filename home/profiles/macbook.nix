{ config, ... }:

let
  dotfiles = "${config.home.homeDirectory}/nixos-dotfiles/config";
  link = path: config.lib.file.mkOutOfStoreSymlink path;
in
{
  home.username = "alex";
  home.homeDirectory = "/Users/alex";

  imports = [
    ../common.nix
    ../packages.nix
    ../packages-macbook.nix
    ../dotfiles.nix
    ../programs/zed-editor.nix
  ];

  # profile specific
  home.file.".ssh/config".source = link "${dotfiles}/ssh/macbook/config";

  programs.direnv = {
    enable = true;
    enableFishIntegration = true;
    nix-direnv.enable = true;
  };

  # Let Home Manager install and manage itself.
  programs.home-manager.enable = true;
}
