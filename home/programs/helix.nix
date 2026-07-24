{ pkgs, ... }:

let
  isDarwin = pkgs.stdenv.hostPlatform.isDarwin;

  localFlake = "(builtins.getFlake (builtins.toString ./.))";

  # Macbook uses standalone Home Manager:
  #
  #   home-manager switch --flake .#alex-macbook
  #
  # NixOS mini uses Home Manager as a NixOS module:
  #
  #   nixos-rebuild switch --flake .#nixos-btw
  homeManagerOptionsExpr =
    if isDarwin then
      "${localFlake}.homeConfigurations.alex-macbook.options"
    else
      "${localFlake}.nixosConfigurations.nixos-btw.options.home-manager.users.type.getSubOptions []";
in
{
  programs.helix = {
    enable = true;

    # Installs Helix and configures both EDITOR and VISUAL as "hx".
    defaultEditor = true;

    /*
      These packages are placed on the PATH of the wrapped hx executable.

      They do not necessarily need to be installed separately in
      home.packages unless you also want to invoke them directly from
      your shell.
    */
    extraPackages = [
      pkgs.nixd
      pkgs.nixfmt

      pkgs.ruff
      pkgs.ty

      pkgs.lua-language-server
      pkgs.marksman
      pkgs.markdown-oxide
      pkgs.harper

      # Provides clangd and clang-format for C development.
      pkgs.llvmPackages_22.clang-tools
    ];

    # Generates ~/.config/helix/config.toml
    settings = {
      theme = "tokyonight_moon";

      editor.file-picker.hidden = false;
    };

    # Generates ~/.config/helix/languages.toml
    languages = {
      language-server = {
        harper-ls = {
          command = "harper-ls";
          args = [ "--stdio" ];
        };
        ruff = {
          command = "ruff";
          args = [ "server" ];
        };

        ty = {
          command = "ty";
          args = [ "server" ];
        };

        nixd = {
          command = "nixd";
          args = [ "--semantic-tokens=true" ];

          config.nixd = {
            formatting.command = [ "nixfmt" ];

            nixpkgs.expr = "import ${localFlake}.inputs.nixpkgs { }";

            options = {
              nixos.expr = "${localFlake}.nixosConfigurations.nixos-btw.options";

              home-manager.expr = homeManagerOptionsExpr;
            };
          };
        };
      };

      language = [
        {
          name = "markdown";
          language-servers = [
            "marksman"
            "markdown-oxide"
            "harper-ls"
          ];
        }
        {
          name = "c";
          file-types = [
            "c"
            "h"
          ];
          auto-format = true;
        }

        {
          name = "python";

          language-servers = [
            {
              name = "ruff";
              only-features = [
                "diagnostics"
                "code-action"
              ];
            }
            {
              name = "ty";
              except-features = [ "format" ];
            }
          ];

          auto-format = true;

          formatter = {
            command = "ruff";
            args = [
              "format"
              "-"
            ];
          };
        }

        {
          name = "nix";
          language-servers = [ "nixd" ];
        }
      ];
    };
  };
}
