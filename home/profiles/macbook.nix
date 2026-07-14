{ config, inputs, ... }:

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
  ];

  nix.nixPath = [ "nixpkgs=${inputs.nixpkgs}"];

  # profile specific
  home.file.".ssh/config".source = link "${dotfiles}/ssh/macbook/config";
}
