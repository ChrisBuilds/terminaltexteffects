"""Verify shipped effects have built-in registration, docs/navigation, permanent tests, and profiling options."""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

from terminaltexteffects.__main__ import build_parser
from tools.perf.benchmark_effects import INPUT_PRESET_NAMES

PROFILE_WORKFLOW = ".github/workflows/profile.yml"


def navigation_paths(value: object) -> set[str]:
    """Collect page paths from navigation values, never labels or unrelated configuration."""
    if isinstance(value, str):
        return {Path(value).as_posix()}
    if isinstance(value, list):
        return {path for item in value for path in navigation_paths(item)}
    if isinstance(value, dict):
        return {path for item in value.values() for path in navigation_paths(item)}
    return set()


def load_navigation(root: Path) -> set[str]:
    """Read only navigation; BaseLoader does not execute custom MkDocs YAML tags."""
    import yaml  # noqa: PLC0415 - Only CLI/docs-loading checks need the locked MkDocs dependency.

    text = (root / "mkdocs.yml").read_text(encoding="utf-8")
    # BaseLoader builds strings/lists/dicts only; it never runs custom/Python constructors.
    config = yaml.load(text, Loader=yaml.BaseLoader)  # noqa: S506
    if not isinstance(config, dict):
        message = "mkdocs.yml must contain a configuration mapping"
        raise TypeError(message)
    return navigation_paths(config.get("nav"))


def load_profile_options(root: Path) -> dict[str, list[str]]:
    """Read the choice options of the Profile workflow's manual inputs."""
    import yaml  # noqa: PLC0415 - Only CLI/docs-loading checks need the locked MkDocs dependency.

    text = (root / PROFILE_WORKFLOW).read_text(encoding="utf-8")
    # BaseLoader keeps the `on` key a string instead of YAML 1.1's boolean `True`.
    workflow = yaml.load(text, Loader=yaml.BaseLoader)  # noqa: S506
    try:
        inputs = workflow["on"]["workflow_dispatch"]["inputs"]
    except (KeyError, TypeError) as error:
        message = f"{PROFILE_WORKFLOW} has no workflow_dispatch inputs"
        raise TypeError(message) from error
    return {name: spec["options"] for name, spec in inputs.items() if isinstance(spec, dict) and "options" in spec}


def check_profile_options(options: dict[str, list[str]], commands: list[str]) -> list[str]:
    """Report Profile workflow drop-downs that no longer list every effect and input preset."""
    expected = {
        "effect": ["all", *sorted(commands)],
        "input_preset": ["medium + large", *INPUT_PRESET_NAMES, "all presets"],
    }
    problems: list[str] = []
    for name, wanted in expected.items():
        actual = options.get(name, [])
        if actual == wanted:
            continue
        missing = [option for option in wanted if option not in actual]
        extra = [option for option in actual if option not in wanted]
        detail = "; ".join(
            part
            for part in (
                f"add {', '.join(missing)}" if missing else "",
                f"remove {', '.join(extra)}" if extra else "",
                "keep the options in order" if not missing and not extra else "",
            )
            if part
        )
        problems.append(
            f"{PROFILE_WORKFLOW} `{name}` options are out of date: {detail}. Expected: {', '.join(wanted)}."
        )
    return problems


def has_test_definitions(path: Path) -> bool:
    """Recognize top-level pytest functions and test methods in Test-prefixed classes."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            return True
        if (
            isinstance(node, ast.ClassDef)
            and node.name.startswith("Test")
            and any(
                isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) and method.name.startswith("test_")
                for method in node.body
            )
        ):
            return True
    return False


def registered_effects() -> dict[str, str]:
    """Map shipped module names to commands without loading plugins or development effects."""
    parser, resources = build_parser(include_user_effects=False)
    commands = {
        name for action in parser._actions if isinstance(action, argparse._SubParsersAction) for name in action.choices
    }
    if commands != resources.keys():
        message = "Built-in CLI subcommands disagree with effect resources; review get_effect_resources/config names."
        raise ValueError(message)
    return {effect.__module__.rsplit(".", 1)[-1]: command for command, (effect, _) in resources.items()}


def check_inventory(root: Path, effects: dict[str, str], navigation: set[str]) -> list[str]:
    """Report missing structural prerequisites; test quality and visuals require separate review."""
    problems: list[str] = []
    modules = {path.stem for path in (root / "terminaltexteffects/effects").glob("effect_*.py")}
    if not modules:
        problems.append("No shipped effect modules found in terminaltexteffects/effects/.")
    problems.extend(
        f"{module}: shipped module is missing from built-in CLI registration."
        for module in sorted(modules - effects.keys())
    )
    problems.extend(
        f"{module}: registered effect has no shipped effect module." for module in sorted(effects.keys() - modules)
    )
    for module, command in sorted(effects.items()):
        page = f"effects/{command}.md"
        document = root / "docs" / page
        if not document.is_file() or not document.read_text(encoding="utf-8").strip():
            problems.append(f"{command} ({module}): missing or empty docs/{page}.")
        if page not in navigation:
            problems.append(f"{command} ({module}): add {page} to mkdocs.yml nav.")
        test = root / "tests/effects_tests" / f"test_{command}.py"
        if not test.is_file():
            problems.append(f"{command} ({module}): missing {test.relative_to(root).as_posix()}.")
        else:
            try:
                if not has_test_definitions(test):
                    problems.append(f"{command}: {test.relative_to(root).as_posix()} has no test definitions.")
            except SyntaxError as error:
                problems.append(f"{command}: invalid Python test file: {error}.")
    return problems


def main() -> int:
    """Validate local shipped inventory with locked development tools; never write files."""
    argparse.ArgumentParser(description=__doc__).parse_args()
    root = Path(__file__).resolve().parents[1]
    effects = registered_effects()
    problems = check_inventory(root, effects, load_navigation(root))
    problems += check_profile_options(load_profile_options(root), list(effects.values()))
    if problems:
        print("Effect inventory failed:\n" + "\n".join(f"- {problem}" for problem in problems), file=sys.stderr)
        return 1
    print(f"Effect inventory passed for {len(effects)} shipped effects. Review test coverage and visuals separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
