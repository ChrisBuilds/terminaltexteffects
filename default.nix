{
  self,
  python312Packages,
}: let
  version = with builtins; (fromTOML (readFile ./pyproject.toml)).tool.poetry.version;
in
  python312Packages.buildPythonApplication {
    pname = "terminaltexteffects";
    inherit version;

    src = self;

    pyproject = true;

    nativeBuildInputs = [
      python312Packages.poetry-core
    ];

    meta.mainProgram = "tte";
  }
