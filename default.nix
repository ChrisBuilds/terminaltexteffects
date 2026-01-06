{
  lib,
  python312Packages,
}: let
  hatchlingDef = with builtins; (fromTOML (readFile ./pyproject.toml)).project;

  name = hatchlingDef.name;
in
  python312Packages.buildPythonApplication {
    pname = name;
    inherit (hatchlingDef) version;

    src = builtins.path {
      path = ./.;
      name = name;
    };

    pyproject = true;

    nativeBuildInputs = [
      python312Packages.hatchling
    ];

    meta = {
      inherit (hatchlingDef) description;
      maintainers = hatchlingDef.authors;
      homepage = "https://github.com/ChrisBuilds/${name}";
      license = lib.licenses.mit;
      mainProgram = "tte";
    };
  }
