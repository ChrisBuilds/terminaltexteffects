{python312Packages}: let
  poetryDef = with builtins; (fromTOML (readFile ./pyproject.toml)).tool.poetry;

  name = poetryDef.name;
in
  python312Packages.buildPythonApplication {
    pname = "terminaltexteffects";
    inherit (poetryDef) version;

    src = builtins.path {
      path = ./.;
      name = name;
    };

    pyproject = true;

    nativeBuildInputs = [
      python312Packages.poetry-core
    ];

    meta.mainProgram = "tte";
  }
