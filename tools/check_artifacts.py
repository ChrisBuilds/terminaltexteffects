"""Build and validate release distributions without publishing them."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tarfile
import tempfile
from email.parser import BytesParser
from pathlib import Path
from zipfile import ZipFile


def run(command: list[str], cwd: Path, *, input_text: str | None = None) -> str:
    """Run an isolated check, preserving diagnostic output and blocking on failure."""
    environment = {name: value for name, value in os.environ.items() if name not in {"PYTHONPATH", "PYTHONHOME"}}
    result = subprocess.run(  # noqa: S603 - Separated arguments; no shell.
        command,
        cwd=cwd,
        env=environment,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode and result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    result.check_returncode()
    return result.stdout


def validate_artifact(artifact: Path, expected_files: set[str], project: dict[str, str]) -> None:
    """Reject missing runtime files or metadata inconsistent with the source project."""
    if artifact.suffix == ".whl":
        with ZipFile(artifact) as archive:
            files = set(archive.namelist())
            metadata_names = [name for name in files if name.endswith(".dist-info/METADATA")]
            if len(metadata_names) != 1:
                msg = f"Expected one wheel metadata file in {artifact.name}."
                raise ValueError(msg)
            metadata = archive.read(metadata_names[0])
    else:
        with tarfile.open(artifact) as archive:
            members = archive.getmembers()
            files = {member.name.partition("/")[2] for member in members if member.isfile()}
            metadata_members = [member for member in members if member.name.partition("/")[2] == "PKG-INFO"]
            if len(metadata_members) != 1:
                msg = f"Expected one source metadata file in {artifact.name}."
                raise ValueError(msg)
            stream = archive.extractfile(metadata_members[0])
            if stream is None:
                msg = f"Cannot read source metadata in {artifact.name}."
                raise ValueError(msg)
            with stream:
                metadata = stream.read()
    missing = expected_files - files
    if missing:
        msg = f"Missing runtime files in {artifact.name}: {', '.join(sorted(missing))}"
        raise ValueError(msg)
    headers = BytesParser().parsebytes(metadata)
    for header, key in (("Name", "name"), ("Version", "version"), ("Requires-Python", "requires-python")):
        if headers[header] != project[key]:
            msg = f"Incorrect {header} in {artifact.name}: {headers[header]!r}, expected {project[key]!r}"
            raise ValueError(msg)


def single_artifact(directory: Path, pattern: str) -> Path:
    """Require exactly one newly built distribution of the requested format."""
    artifacts = list(directory.glob(pattern))
    if len(artifacts) != 1:
        msg = f"Expected exactly one {pattern} in {directory}; found {len(artifacts)}."
        raise ValueError(msg)
    return artifacts[0]


def smoke_install(wheel: Path, scratch: Path, label: str) -> None:
    """Test an artifact in a clean environment outside the repository."""
    environment = scratch / label
    outside = scratch / "outside-checkout"
    outside.mkdir(exist_ok=True)
    run(["uv", "venv", "--python", sys.executable, str(environment)], outside)
    binaries = environment / ("Scripts" if os.name == "nt" else "bin")
    python = binaries / ("python.exe" if os.name == "nt" else "python")
    run(["uv", "pip", "install", "--python", str(python), str(wheel)], outside)
    smoke = (
        "import importlib, pathlib, pkgutil, sys, terminaltexteffects; "
        "installed = pathlib.Path(terminaltexteffects.__file__).resolve(); "
        "assert installed.is_relative_to(pathlib.Path(sys.prefix).resolve()); "
        "import terminaltexteffects.effects; "
        "[importlib.import_module(module.name) for module in pkgutil.iter_modules("
        "terminaltexteffects.effects.__path__, terminaltexteffects.effects.__name__ + '.')]; "
        "print('Installed package and effect modules imported successfully.')"
    )
    run([str(python), "-I", "-c", smoke], outside)
    for entry in ("tte", "terminaltexteffects"):
        executable = binaries / (f"{entry}.exe" if os.name == "nt" else entry)
        help_text = run([str(executable), "--help"], outside)
        if "wipe" not in help_text:
            msg = f"{entry} did not register the Wipe effect."
            raise ValueError(msg)
        output = run(
            [
                str(executable),
                "--seed",
                "92",
                "--frame-rate",
                "0",
                "--no-color",
                "--canvas-width",
                "2",
                "--canvas-height",
                "1",
                "--ignore-terminal-dimensions",
                "wipe",
                "--final-gradient-stops",
                "ffffff",
                "--final-gradient-steps",
                "1",
                "--final-gradient-frames",
                "1",
            ],
            outside,
            input_text="OK",
        )
        if "OK" not in output:
            msg = f"{entry} did not render the smoke-test input."
            raise ValueError(msg)


def check_artifacts(root: Path, scratch: Path, output: Path) -> None:
    """Build both formats, rebuild from the archive, and validate two clean installations."""
    import tomli  # noqa: PLC0415 - Keep archive unit tests independent of optional build tools.

    if output.exists() and any(output.iterdir()):
        msg = f"Artifact output must be empty: {output}"
        raise ValueError(msg)
    output.mkdir(parents=True, exist_ok=True)
    project = tomli.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    tracked = run(["git", "ls-files", "-z", "--", "terminaltexteffects"], root)
    expected = {name for name in tracked.split("\0") if name}
    if not expected:
        msg = "No tracked runtime package files found."
        raise ValueError(msg)
    constraints = scratch / "build-constraints.txt"
    run(
        [
            "uv",
            "export",
            "--locked",
            "--only-group",
            "artifacts",
            "--no-emit-project",
            "--format",
            "requirements.txt",
            "--output-file",
            str(constraints),
        ],
        root,
    )
    build_options = ["--python", sys.executable, "--no-sources", "--build-constraints", str(constraints)]
    print("Building the wheel and source distribution.", flush=True)
    run(["uv", "build", str(root), "--sdist", "--wheel", *build_options, "--out-dir", str(output)], root)
    direct = single_artifact(output, "*.whl")
    source = single_artifact(output, "*.tar.gz")
    rebuilt_directory = output / "from-sdist"
    run(["uv", "build", str(source), "--wheel", *build_options, "--out-dir", str(rebuilt_directory)], scratch)
    rebuilt = single_artifact(rebuilt_directory, "*.whl")
    for artifact in (direct, source, rebuilt):
        validate_artifact(artifact, expected, project)
    run([sys.executable, "-m", "twine", "check", "--strict", str(direct), str(source), str(rebuilt)], scratch)
    print("Checking clean installations of both wheels.", flush=True)
    smoke_install(direct, scratch, "direct-wheel")
    smoke_install(rebuilt, scratch, "rebuilt-wheel")
    print("Release artifact validation passed.")


def main() -> int:
    """Validate distributions, optionally retaining them in a fresh output directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="Empty directory to retain validated artifacts.")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        with tempfile.TemporaryDirectory(prefix="tte-artifacts-") as temporary:
            scratch = Path(temporary)
            output = args.output_dir.resolve() if args.output_dir else scratch / "dist"
            check_artifacts(root, scratch, output)
    except (ValueError, subprocess.CalledProcessError) as error:
        print(f"Artifact validation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
