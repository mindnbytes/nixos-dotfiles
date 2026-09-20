{ pkgs, pkgsUnstable, ... }:

let
  llvm22 = pkgs.llvmPackages_22;
in
{
  fonts.fontconfig.enable = true;

  home.packages = [
    pkgs.nerd-fonts.fira-code
    pkgsUnstable.wezterm
    pkgsUnstable.llama-cpp
    pkgs.ghostty-bin

    # Stable LLVM 22 toolchain
    llvm22.clang
    llvm22.clang-tools
    llvm22.lld
    llvm22.llvm
    llvm22.compiler-rt
    # Python dev tools
    pkgs.uv
    # Dev-machine only
    pkgs.go
  ];
}
