{
  lib,
  python3Packages,
}: let
  hatchlingDef = with builtins; (fromTOML (readFile ./pyproject.toml)).project;

  name = hatchlingDef.name;
in
  python3Packages.buildPythonApplication {
    pname = name;
    inherit (hatchlingDef) version;

    src = lib.cleanSourceWith {
      src = ./.;
      name = name;
      filter = path: type: let
        relative = lib.removePrefix (toString ./. + "/") (toString path);
        base = baseNameOf path;
      in
        (builtins.elem relative ["pyproject.toml" "README.md" "LICENSE"]
          || relative == "terminaltexteffects"
          || lib.hasPrefix "terminaltexteffects/" relative)
        && base != "__pycache__"
        && !(lib.hasSuffix ".pyc" base)
        && !(lib.hasSuffix ".pyo" base)
        && !(lib.hasSuffix "~" base)
        && !(lib.hasSuffix ".swp" base)
        && base != "effect_dev.py";
    };

    pyproject = true;

    build-system = [
      python3Packages.hatchling
    ];

    pythonImportsCheck = ["terminaltexteffects"];

    meta = {
      inherit (hatchlingDef) description;
      maintainers = hatchlingDef.authors;
      homepage = "https://github.com/ChrisBuilds/${name}";
      license = lib.licenses.mit;
      mainProgram = "tte";
    };
  }
