{
  description = "NixOs and Home Manager dotfiles";

  inputs = {
    nixpkgs.url = "nixpkgs/nixos-26.05";

    home-manager = {
      url = "github:nix-community/home-manager/release-26.05";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      home-manager,
      ...
    }:
    let
      mkPkgs =
        system:
        import nixpkgs {
          inherit system;
          # Uncomment if you need proprietary packages
          # config.allowUnfree = true;
        };
    in
    {
      nixosConfigurations.nixos-btw = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";

        modules = [
          ./hosts/nixos-btw/configuration.nix

          home-manager.nixosModules.home-manager
          {
            home-manager.useGlobalPkgs = true;
            home-manager.useUserPackages = true;
            home-manager.backupFileExtension = "backup";

            home-manager.users.alex = import ./home/profiles/nixos-mini.nix;
          }
        ];
      };

      homeConfigurations.alex-macbook = home-manager.lib.homeManagerConfiguration {
        pkgs = mkPkgs "aarch64-darwin";

        modules = [
          ./home/profiles/macbook.nix
        ];
      };
    };
}
