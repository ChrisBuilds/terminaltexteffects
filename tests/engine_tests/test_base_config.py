"""Unit tests for BaseConfig config-construction behavior."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import pytest

from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.utils import argutils

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


def test_build_config_none_uses_argspec_defaults() -> None:
    """Build config from declared ArgSpec defaults when parsed args are not provided."""
    config: ExampleConfig = ExampleConfig._build_config(None)
    assert config.alpha == 1
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
