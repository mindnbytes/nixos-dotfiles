{
  config,
  ...
}:

let
  dotfiles = "${config.home.homeDirectory}/nixos-dotfiles/config";
  link = path: config.lib.file.mkOutOfStoreSymlink path;

  commonConfigs = {
    git = "git";
  };
in
{
  xdg.configFile =
    builtins.mapAttrs (_name: subpath: {
      source = link "${dotfiles}/${subpath}";
      recursive = true;
    }) commonConfigs;
}
