{ pkgs, ... }:

{
  fonts.fontconfig.enable = true;

  home.packages = with pkgs; [
    nerd-fonts.fira-code

    wezterm
    wget
    gh
    fastfetch
    ripgrep
    fd
    jq
    eza
    bat
    btop
  ];
}
