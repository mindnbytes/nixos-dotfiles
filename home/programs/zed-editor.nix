{ pkgs, pkgsUnstable, ... }:

let
  isDarwin = pkgs.stdenv.hostPlatform.isDarwin;

  localFlake = "(builtins.getFlake (builtins.toString ./.))";

  homeManagerOptionsExpr =
    if isDarwin then
      "${localFlake}.homeConfigurations.alex-macbook.options"
    else
      "${localFlake}.nixosConfigurations.nixos-btw.options.home-manager.users.type.getSubOptions []";
in
{
  # Many default configuration options are skipped, check Zed config reference
  programs.zed-editor = {
    enable = true;
    package = pkgsUnstable.zed-editor;
    extraPackages = [
      pkgs.nixd
      pkgs.nixfmt
      pkgs.dockerfile-language-server
    ];
    extensions = [
      "nix"
      "dockerfile"
      "catppuccin"
      "catppuccin-icons"
    ];
    userKeymaps = [
      {
        context = "Workspace";
        bindings = {
          "ctrl-w t" = "terminal_panel::ToggleFocus";
        };
      }
    ];

    userSettings = {
      helix_mode = true; # helix mode is on top of vim mode

      ######### Themes, fonts, visuals #########
      theme = "Catppuccin Frappé";
      icon_theme = "Catppuccin Frappé";
      # UI Font. Use ".SystemUIFont" to use the default system font (SF Pro on macOS),
      # or ".ZedSans" for the bundled default (currently IBM Plex)
      ui_font_family = ".SystemUIFont";
      ui_font_weight = 400; # Font weight in standard CSS units from 100 to 900.
      ui_font_size = 16;
      # Buffer Font - Used by editor buffers
      # use ".ZedMono" for the bundled default monospace (currently Lilex)
      buffer_font_family = "JetBrainsMono Nerd Font Mono";
      buffer_font_size = 15;
      buffer_font_weight = 400;
      # Line height "comfortable" (1.618), "standard" (1.3) or custom: `{ "custom": 2 }`
      buffer_line_height = "comfortable";
      # Editor
      cursor_blink = false;
      cursor_shape = "bar";
      autosave = "on_focus_change";
      colorize_brackets = true;
      ######### AI agents, models, edit predictions #########
      agent = {
        default_model = {
          provider = "openai-subscribed";
          model = "gpt-5.6-luna";
          enable_thinking = true;
          effort = "high";
        };

        profiles = {
          "insightful-code-review" = {
            name = "Insightful Code Review";

            # Keep reviews observational: inspect the project and diagnostics,
            # but do not modify files, execute commands, or access the network.
            tools = {
              diagnostics = true;
              find_path = true;
              grep = true;
              list_directory = true;
              read_file = true;
              skill = true;

              create_directory = false;
              delete_path = false;
              edit_file = false;
              fetch = false;
              move_path = false;
              search_web = false;
              spawn_agent = false;
              terminal = false;
              write_file = false;
            };

            enable_all_context_servers = false;
            context_servers = { };

            default_model = {
              provider = "openai-subscribed";
              model = "gpt-5.6-sol";
              enable_thinking = true;
              effort = "high";
            };
          };
        };

        auto_compact = {
          enabled = true;
          threshold = "90%";
        };
      };

      # Defuault provider but don't show unless triggered manually
      edit_predictions = {
        provider = "zed";
        mode = "subtle";
      };
      show_edit_predictions = false;
      # File Finder
      file_finder = {
        modal_max_width = "medium";
        include_ignored = "smart";
      };

      ######### Terminal #########
      terminal = {
        dock = "right";
        default_width = 320;
        blinking = "off";
        cursor_shape = "bar";

        font_family = "JetBrainsMono Nerd Font";
        font_size = 13;
        line_height = "comfortable";

        shell = "system";
        env = {
          EDITOR = "zed --wait";
          VISUAL = "zed --wait";
        };
      };

      ######### Languages and LSPs #########
      languages = {
        Nix = {
          language_servers = [
            "nixd"
            "!nil"
          ];
          formatter = {
            external = {
              command = "nixfmt";
            };
          };
          format_on_save = "on";
        };
      };
      # LSP
      lsp = {
        nixd = {
          settings = {
            nixd = {
              formatting.command = [ "nixfmt" ];

              nixpkgs.expr = "import ${localFlake}.inputs.nixpkgs { }";

              options = {
                nixos.expr = "${localFlake}.nixosConfigurations.nixos-btw.options";
                home-manager.expr = homeManagerOptionsExpr;
              };

              diagnostic.suppress = [ "sema-extra-with" ];
            };
          };
        };
      };
    };
  };
}
