{
  description = "NixOs and Home Manager dotfiles";

  inputs = {
    nixpkgs.url = "nixpkgs/nixos-26.05";
    nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixos-unstable";

    home-manager = {
      url = "github:nix-community/home-manager/release-26.05";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    inputs@{
      self,
      nixpkgs,
      home-manager,
      ...
    }:
    let
      mkPkgs =
        nixpkgsInput: system:
        import nixpkgsInput {
          inherit system;
          # Uncomment if you need proprietary packages
          # config.allowUnfree = true;
        };
    in
    {
      nixosConfigurations.nixos-btw =
        let
          system = "x86_64-linux";
        in
        nixpkgs.lib.nixosSystem {
          system = system;

          modules = [
            ./hosts/nixos-btw/configuration.nix

            home-manager.nixosModules.home-manager
            {
              home-manager.useGlobalPkgs = true;
              home-manager.useUserPackages = true;
              home-manager.backupFileExtension = "backup";

              home-manager.extraSpecialArgs = {
                inherit inputs;
                pkgsUnstable = mkPkgs inputs.nixpkgs-unstable system;
              };

              home-manager.users.alex = import ./home/profiles/nixos-mini.nix;
            }
          ];
        };

      homeConfigurations.alex-macbook =
        let
          system = "aarch64-darwin";
        in
        home-manager.lib.homeManagerConfiguration {
          pkgs = mkPkgs nixpkgs system;

          extraSpecialArgs = {
            inherit inputs;
            pkgsUnstable = mkPkgs inputs.nixpkgs-unstable system;
          };

          modules = [
            ./home/profiles/macbook.nix
          ];
        };
    };
}
