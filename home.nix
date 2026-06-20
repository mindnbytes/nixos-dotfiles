{ config, pkgs, ... }:

let
  dotfiles = "${config.home.homeDirectory}/nixos-dotfiles/config";
  create_symlink = path: config.lib.file.mkOutOfStoreSymlink path;
  # Standard .config/directory
  configs = {
    qtile = "qtile";
    helix = "helix";
    wezterm = "wezterm";
    git = "git";
  };
in

{
  home.username = "alex";
  home.homeDirectory = "/home/alex";
  home.stateVersion = "26.05";
  programs.fish = {
    enable = true;
    shellAliases = {
      btw = "echo i use nixos, btw";
      la = "ls -la";
    };
  };
  # dot configs
  xdg.configFile = builtins.mapAttrs (name: subpath: {
    source = create_symlink "${dotfiles}/${subpath}";
    recursive = true;
  }) configs;

  # manual mapping configs
  home.file.".ssh/config" = {
    source = create_symlink "${dotfiles}/ssh/config";
  };

  home.packages = with pkgs; [
    nil
    nixpkgs-fmt
    lua-language-server
    fastfetch
    gh
  ];
}
