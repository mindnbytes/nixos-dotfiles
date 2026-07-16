{ lib, pkgs, ... }:

{
  programs.fish = {
    enable = true;

    # Home Manager generates completions from the man pages of installed
    # packages. This is already true by default, but keeping it explicit
    # documents why manual completion links are unnecessary.
    generateCompletions = true;

    interactiveShellInit = ''
      set -g fish_greeting
      set -gx COLORTERM truecolor
    ''
    + lib.optionalString pkgs.stdenv.isDarwin ''
      # Homebrew is outside Nix, so detect its architecture-specific path
      # at shell startup.
      if test -d /opt/homebrew/bin
        fish_add_path --global /opt/homebrew/bin /opt/homebrew/sbin
      else if test -d /usr/local/bin
        fish_add_path --global /usr/local/bin /usr/local/sbin
      end
    '';

    functions.la = {
      description = "List all files with details and icons";
      wraps = "eza";
      body = ''
        eza -lah --icons $argv
      '';
    };
  };

  programs.starship = {
    enable = true;
    enableFishIntegration = true;
  };

  programs.zoxide = {
    enable = true;
    enableFishIntegration = true;
  };
}
