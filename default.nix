{
  self,
  version,
  python312Packages,
}:
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
