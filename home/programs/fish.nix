{
  config,
  lib,
  pkgs,
  ...
}:

{
  home.sessionPath = [
    "${config.home.profileDirectory}/bin"
  ]
  ++ lib.optionals pkgs.stdenv.isDarwin [
    "/nix/var/nix/profiles/default/bin"
    "/opt/homebrew/bin"
    "/opt/homebrew/sbin"
  ];

  programs.man = {
    enable = true;

    # Home Manager's Fish module currently enables this by default,
    # but macOS has no configured man package for building apropos caches.
    generateCaches = pkgs.stdenv.isLinux;
  };

  programs.fish = {
    enable = true;

    # explicitly add vendor completions for now, I don't thinks it is supposed to be this way
    shellInitLast = ''
      set -l hm_vendor_completions \
        "$HOME/.nix-profile/share/fish/vendor_completions.d"

      if test -d "$hm_vendor_completions"
        set -p fish_complete_path "$hm_vendor_completions"
      end
    ''
    + lib.optionalString pkgs.stdenv.isDarwin ''
      set -l nix_vendor_completions \
        /nix/var/nix/profiles/default/share/fish/vendor_completions.d

      if test -d "$nix_vendor_completions"
        set -p fish_complete_path "$nix_vendor_completions"
      end
    '';

    generateCompletions = false;

    interactiveShellInit = ''
      set -g fish_greeting
      set -gx COLORTERM truecolor
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
