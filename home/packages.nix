{ pkgs, ... }:

{
  home.packages = with pkgs; [
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
