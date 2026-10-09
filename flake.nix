{
  description = "Visual effects applied to text in the terminal. ";

  inputs = {
    nixpkgs.url = "https://channels.nixos.org/nixpkgs-unstable/nixexprs.tar.zst";
    systems.url = "github:nix-systems/default";
  };

  outputs = {
    systems,
    nixpkgs,
    ...
  }: let
    forEachSystem = f: nixpkgs.lib.genAttrs (import systems) (system: f nixpkgs.legacyPackages.${system});
  in {
    formatter = forEachSystem (pkgs: pkgs.alejandra);

    packages = forEachSystem (pkgs: {
      default = pkgs.callPackage ./default.nix {};
    });
  };
}
