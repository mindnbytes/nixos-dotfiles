{ config, pkgs }:

let
  # Resolve the live checkout independently of the editor's working directory.
  flake = "(builtins.getFlake ${builtins.toJSON "${config.home.homeDirectory}/nixos-dotfiles"})";
  system = builtins.toJSON pkgs.stdenv.hostPlatform.system;
in
{
  formatting.command = [ "nixfmt" ];

  nixpkgs.expr = "import ${flake}.inputs.nixpkgs { system = ${system}; }";

  options = {
    nixos.expr = "${flake}.nixosConfigurations.nixos-btw.options";
    home-manager.expr =
      if pkgs.stdenv.hostPlatform.isDarwin then
        "${flake}.homeConfigurations.alex-macbook.options"
      else
        "${flake}.nixosConfigurations.nixos-btw.options.home-manager.users.type.getSubOptions []";
  };
}
