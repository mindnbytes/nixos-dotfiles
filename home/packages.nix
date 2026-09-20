{ pkgs, ... }:

{
  home.packages = with pkgs; [
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
