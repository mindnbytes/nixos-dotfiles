{
  config,
  pkgs,
  ...
}:

let
  dotfiles = "${config.home.homeDirectory}/nixos-dotfiles/config";
  link = path: config.lib.file.mkOutOfStoreSymlink path;

  commonConfigs = {
    git = "git";
    wezterm = "wezterm";
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

      "fish/completions/nix.fish".source = "${pkgs.nix}/share/fish/vendor_completions.d/nix.fish";

      "fish/completions/home-manager.fish".source =
        "${config.programs.home-manager.package}/share/fish/vendor_completions.d/home-manager.fish";
    };
}
