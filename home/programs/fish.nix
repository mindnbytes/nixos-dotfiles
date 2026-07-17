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

    shellInitLast = lib.optionalString pkgs.stdenv.isDarwin ''
      # Home Manager's aggregate profile contains package-provided Fish
      # completions, but Fish on macOS does not discover these profile
      # directories automatically.
      for dir in \
        "${config.home.profileDirectory}/share/fish/vendor_completions.d" \
        "/nix/var/nix/profiles/default/share/fish/vendor_completions.d"

        if test -d "$dir"; and not contains -- "$dir" $fish_complete_path
          set -p fish_complete_path "$dir"
        end
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
