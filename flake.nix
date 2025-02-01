{
  description = "A collection of anyfs structure program";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-unstable";
    anyfs = {
      url = "github:igsha/anyfs";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, anyfs }: let
    pkgs = nixpkgs.legacyPackages.x86_64-linux;
  in {
    packages.x86_64-linux = rec {
      anyfs-collection = pkgs.callPackage ./default.nix { };
      default = anyfs-collection;
    };
    devShells.x86_64-linux.default = with pkgs; mkShell {
      inputsFrom = [ self.packages.x86_64-linux.anyfs-collection ];
      nativeBuildInputs = [ anyfs.packages.${pkgs.system}.anyfs ];
      PYTHONDONTWRITEBYTECODE = 1;
    };
  };
}
