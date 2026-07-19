{ config, ... }:

let
  dotfiles = "${config.home.homeDirectory}/nixos-dotfiles/config";
  link = path: config.lib.file.mkOutOfStoreSymlink path;
in
{
  home.username = "alex";
  home.homeDirectory = "/home/alex";

  imports = [
    ../common.nix
    ../packages.nix
    ../dotfiles.nix
  ];
  # profile specific
  home.file.".ssh/config".source = link "${dotfiles}/ssh/nixos-mini/config";
}
