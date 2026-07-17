{ pkgs, pkgsUnstable, ... }:

let
  llvm22 = pkgs.llvmPackages_22;
in
{
  home.packages = [
    pkgsUnstable.llama-cpp
    pkgsUnstable.opencode

    # Stable LLVM 22 toolchain
    llvm22.clang
    llvm22.clang-tools
    llvm22.lld
    llvm22.llvm
    llvm22.compiler-rt
    # Python dev tools
    pkgs.uv
  ];
}
