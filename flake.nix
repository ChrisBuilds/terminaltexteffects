{
  description = "Visual effects applied to text in the terminal. ";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    systems.url = "github:nix-systems/default";
  };

  outputs = {
    self,
    systems,
    nixpkgs,
  }: let
    forEachSystem = f: nixpkgs.lib.genAttrs (import systems) (system: f nixpkgs.legacyPackages.${system});

    version = with builtins; (fromTOML (readFile ./pyproject.toml)).tool.poetry.version;
  in {
    formatter = forEachSystem (pkgs: pkgs.alejandra);

    packages = forEachSystem (pkgs: {
      default = pkgs.callPackage ./default.nix {inherit version self;};
    });
  };
}
