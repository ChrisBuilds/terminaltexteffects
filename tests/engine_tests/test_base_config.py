"""Unit tests for BaseConfig config-construction behavior."""

from __future__ import annotations

import argparse
import importlib
import pkgutil
from dataclasses import dataclass

import pytest

from terminaltexteffects.effects import __name__ as effects_name
from terminaltexteffects.effects import __path__ as effects_path
from terminaltexteffects.effects.effect_laseretch import LaserEtchConfig
from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.utils import argutils, easing
from terminaltexteffects.utils.graphics import Color, Gradient

pytestmark = [pytest.mark.engine, pytest.mark.smoke]


@dataclass
class ExampleConfig(BaseConfig):
    """Config model using only ArgSpec-backed fields."""

    parser_spec: argutils.ParserSpec = argutils.ParserSpec(
        name="example",
        help="example help",
        description="example description",
        epilog="example epilog",
    )
    alpha: int = argutils.ArgSpec(name="--alpha", default=1, type=int)  # pyright: ignore[reportAssignmentType]
    beta: str = argutils.ArgSpec(name="--beta", default="b")  # pyright: ignore[reportAssignmentType]


@dataclass
class ExampleStrictConfig(BaseConfig):
    """Config model including a non-ArgSpec field for strict missing-field checks."""

    parser_spec: argutils.ParserSpec = argutils.ParserSpec(
        name="strict",
        help="strict help",
        description="strict description",
        epilog="strict epilog",
    )
    alpha: int = argutils.ArgSpec(name="--alpha", default=10, type=int)  # pyright: ignore[reportAssignmentType]
    gamma: int = 42


@dataclass
class NormalizedConfig(BaseConfig):
    """Config exercising shared direct-construction and assignment validation."""

    parser_spec: argutils.ParserSpec = ExampleConfig.parser_spec
    count: int = argutils.ArgSpec(name="--count", default=1, type=argutils.PositiveInt.type_parser)  # pyright: ignore[reportAssignmentType]
    choice: str = argutils.ArgSpec(name="--choice", default="one", choices=["one", "two"])  # pyright: ignore[reportAssignmentType]
    enabled: bool = argutils.ArgSpec(name="--enabled", default=False, action="store_true")  # pyright: ignore[reportAssignmentType]
    colors: tuple[Color, ...] = argutils.ArgSpec(  # pyright: ignore[reportAssignmentType]
        name="--colors",
        default=(Color(1),),
        type=argutils.ColorArg.type_parser,
        nargs="+",
        action=argutils.TupleAction,
    )
    direction: Gradient.Direction = argutils.ArgSpec(  # pyright: ignore[reportAssignmentType]
        name="--direction",
        default=Gradient.Direction.VERTICAL,
        type=argutils.GradientDirection.type_parser,
    )
    ease: object = argutils.ArgSpec(name="--ease", default=easing.linear, type=argutils.Ease.type_parser)  # pyright: ignore[reportAssignmentType]
    span: tuple[int, int] = argutils.ArgSpec(  # pyright: ignore[reportAssignmentType]
        name="--span", default=(1, 2), type=argutils.PositiveIntRange.type_parser,
    )


def test_build_config_none_uses_argspec_defaults() -> None:
    """Build config from declared ArgSpec defaults when parsed args are not provided."""
    config: ExampleConfig = ExampleConfig._build_config(None)
    assert config.alpha == 1
    assert config.beta == "b"


def test_direct_config_uses_argspec_defaults() -> None:
    """Direct construction should resolve `ArgSpec` defaults for library users."""
    config = ExampleConfig()

    assert config.alpha == 1
    assert config.beta == "b"


def test_direct_config_preserves_explicit_values() -> None:
    """Direct construction should retain values passed by the caller."""
    config = ExampleConfig(alpha=7)

    assert config.alpha == 7
    assert config.beta == "b"


def test_build_config_full_namespace_uses_namespace_values() -> None:
    """Use all provided namespace values when every field is present."""
    parsed_args: argparse.Namespace = argparse.Namespace(alpha=7, beta="z")
    config: ExampleConfig = ExampleConfig._build_config(parsed_args)
    assert config.alpha == 7
    assert config.beta == "z"


def test_build_config_partial_namespace_falls_back_to_argspec_default() -> None:
    """Fallback to ArgSpec defaults for fields missing from a partial namespace."""
    parsed_args: argparse.Namespace = argparse.Namespace(alpha=7)
    config: ExampleConfig = ExampleConfig._build_config(parsed_args)
    assert config.alpha == 7
    assert config.beta == "b"


def test_build_config_ignores_parser_spec_attribute_on_namespace() -> None:
    """Ignore parser metadata during config construction from namespace values."""
    parsed_args: argparse.Namespace = argparse.Namespace(alpha=3, beta="y")
    config: ExampleConfig = ExampleConfig._build_config(parsed_args)
    assert config.alpha == 3
    assert config.beta == "y"


def test_build_config_missing_non_argspec_field_raises_attribute_error() -> None:
    """Raise a clear error when a non-ArgSpec field is absent in parsed args."""
    parsed_args: argparse.Namespace = argparse.Namespace(alpha=12)
    with pytest.raises(AttributeError, match="Missing required config field 'gamma' for ExampleStrictConfig"):
        ExampleStrictConfig._build_config(parsed_args)


def test_direct_config_normalizes_and_validates_values() -> None:
    """Direct construction accepts CLI spellings and native library values."""
    config = NormalizedConfig(
        count="3",  # pyright: ignore[reportArgumentType]
        choice="two",
        enabled=True,
        colors=["2", Color("ffffff")],  # pyright: ignore[reportArgumentType]
        direction="horizontal",  # pyright: ignore[reportArgumentType]
        span=[1, 3],  # pyright: ignore[reportArgumentType]
    )

    assert config.count == 3
    assert config.colors == (Color(2), Color("ffffff"))
    assert config.direction is Gradient.Direction.HORIZONTAL
    assert config.span == (1, 3)


@pytest.mark.parametrize(
    ("field", "value"),
    [("count", 0), ("choice", "invalid"), ("enabled", 1), ("colors", [Color(1), "invalid"]), ("span", (2, 1))],
)
def test_config_assignment_validates_values(field: str, value: object) -> None:
    """Mutation follows the same validation contract as construction."""
    config = NormalizedConfig()
    with pytest.raises(ValueError, match=field):
        setattr(config, field, value)


def test_tuple_action_accepts_scalar_and_custom_ease() -> None:
    """Tuple fields canonicalize scalars while easing fields preserve custom callables."""
    custom_ease = lambda value: value  # noqa: E731
    config = NormalizedConfig(colors="3", ease=custom_ease)  # pyright: ignore[reportArgumentType]

    assert config.colors == (Color(3),)
    assert config.ease is custom_ease


def test_plugin_style_int_parser_is_used_for_direct_construction() -> None:
    """Third-party `ArgSpec.type` callables normalize direct library values too."""
    assert ExampleConfig(alpha="7").alpha == 7  # pyright: ignore[reportArgumentType]


def test_build_config_preserves_omitted_tuple_action_default_representation() -> None:
    """Omitted CLI defaults retain declarations such as scalar gradient steps."""
    parser = argparse.ArgumentParser()
    LaserEtchConfig._populate_parser(parser)

    assert LaserEtchConfig._build_config(parser.parse_args([])).final_gradient_steps == 8


def _builtin_config_types() -> list[type[BaseConfig]]:
    config_types: list[type[BaseConfig]] = []
    for module_info in pkgutil.iter_modules(effects_path, effects_name + "."):
        module = importlib.import_module(module_info.name)
        if hasattr(module, "get_effect_resources"):
            config_types.append(module.get_effect_resources()[2])
    return config_types


@pytest.mark.parametrize("config_type", _builtin_config_types())
def test_all_builtin_configs_construct_from_defaults(config_type: type[BaseConfig]) -> None:
    """All built-in declarations satisfy the shared normalization contract."""
    config_type()
