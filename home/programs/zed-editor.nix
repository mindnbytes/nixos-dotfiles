{ pkgs, pkgsUnstable, ... }:
{
  # Many default configuration options are skipped, check Zed config reference
  programs.zed-editor = {
    enable = true;
    package = pkgsUnstable.zed-editor;
    extraPackages = [
      pkgs.nixd
      pkgs.nixfmt
    ];
    extensions = [
      "nix"
      "dockerfile"
      "catppuccin"
      "catppuccin-icons"
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
      buffer_font_family = ".ZedMono";
      buffer_font_size = 15;
      buffer_font_weight = 400;
      # Line height "comfortable" (1.618), "standard" (1.3) or custom: `{ "custom": 2 }`
      buffer_line_height = "comfortable";
      # Editor
      cursor_blink = false;
      cursor_shape = "bar";
      autosave = "on_focus_change";
      ######### AI agents, models, edit predictions #########
      agent = {
        default_model = {
          provider = "openai-subscribed";
          model = "gpt-5.6-luna";
          enable_thinking = true;
          effort = "high";
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
        blinking = "off";
        cursor_shape = "bar";

        font_family = "FiraCode Nerd Font";
        font_size = 13;
        line_height = "comfortable";

        shell = "system";
        env = {
          EDITOR = "zed --wait";
          TERM = "ghostty";
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
            diagnostic = {
              suppress = [ "sema-extra-with" ];
            };
          };
        };
      };
    };
  };
}
