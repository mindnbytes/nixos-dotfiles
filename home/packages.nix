{ pkgs, ... }:

{
  fonts.fontconfig.enable = true;

  home.packages = with pkgs; [
    nil
    nixpkgs-fmt
    lua-language-server

    nerd-fonts.fira-code

    fish
    starship
    helix
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
