{ pkgs, ... }:

{
  fonts.fontconfig.enable = true;

  home.packages = with pkgs; [
    nerd-fonts.fira-code

    fish
    starship
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
    zoxide
  ];
}
