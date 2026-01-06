{
  lib,
  python312Packages,
}: let
  projectDef = with builtins; (fromTOML (readFile ./pyproject.toml)).project;

  inherit (projectDef) name;
in
  python312Packages.buildPythonApplication {
    pname = name;
    inherit (projectDef) version;

    src = builtins.path {
      path = ./.;
      inherit name;
    };

    pyproject = true;

    nativeBuildInputs = [
      python312Packages.hatchling
    ];

    meta = {
      inherit (projectDef) description;
      maintainers = projectDef.authors;
      homepage = "https://github.com/ChrisBuilds/${name}";
      license = lib.licenses.mit;
      mainProgram = "tte";
    };
  }
