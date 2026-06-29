{
  config,
  lib,
  pkgs,
  ...
}:

let
  dotfiles = "${config.home.homeDirectory}/nixos-dotfiles/config";
  link = path: config.lib.file.mkOutOfStoreSymlink path;

  commonConfigs = {
    git = "git";
    wezterm = "wezterm";
    helix = "helix";
  };
in
{
  xdg.configFile =
    builtins.mapAttrs (_name: subpath: {
      source = link "${dotfiles}/${subpath}";
      recursive = true;
    }) commonConfigs
    // {
      "starship.toml".source = link "${dotfiles}/starship/starship.toml";

      "fish/config.fish" = {
        source = link "${dotfiles}/fish/config.fish";
      };

      "fish/functions" = {
        source = link "${dotfiles}/fish/functions";
        recursive = true;
      };
    };
}
