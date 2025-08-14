"""Base effect configuration classes.

The BaseConfig and ArgSpec classes facilitate specifying an effect configuration and using
that specification to populate an argparse ArgumentParser. The resulting parsed argparse
Namespace can be used to construct the effect configuration. If the concrete effect
class is instantiated without passing an argparse Namespace, the class fields are
parsed to determine the default values used in the dataclass constructor.
"""

from __future__ import annotations

import argparse
import typing
from dataclasses import dataclass, fields

MISSING = object()


@dataclass(frozen=True)
class ArgSpec:
    """Specification for a command-line argument and default value.

    The default value is used for both the argparse argument and to support direct
    instantiation of a config.
    """

    name: str
    default: typing.Any
    metavar: str = MISSING  # type: ignore[arg-type]
    type: typing.Any = MISSING  # type: ignore[arg-type]
    required: bool = MISSING  # type: ignore[arg-type]
    help: str = MISSING  # type: ignore[arg-type]


@dataclass
class BaseConfig:
    """
    Base configuration class for effects.

    This class serves as a base for all effect configurations, providing a common
    interface for argument parsing and configuration building. All sub-classes
    must implement the `_get_config` method to return their specific configuration
    class. Any config class intended to be used to populate a subparser must
    define a `subparser_data` class variable.
    """

    subparser_data: typing.ClassVar[dict[str, str]]

    @classmethod
    def _populate_parser(cls, parser: argparse.ArgumentParser | argparse._SubParsersAction) -> None:
        """Populate the argument parser with the effect's configuration options.

        If a subparser is being populated, the subparser_data will be used to
        configure the subparser defaults.
        """
        if isinstance(parser, argparse._SubParsersAction):
            parser = parser.add_parser(**cls.subparser_data)  # type: ignore[arg-type]

        assert isinstance(parser, argparse.ArgumentParser)
        for field in fields(cls):
            spec = field.default
            assert isinstance(spec, ArgSpec)
            add_args_sig = {k: v for k, v in vars(spec).items() if v is not MISSING}
            parser.add_argument(add_args_sig.pop("name"), **add_args_sig)

    @classmethod
    def _build_config(cls: type[CONFIG], parsed_args: argparse.Namespace | None = None) -> CONFIG:
        """Build the effect configuration from the parsed arguments or argument specifications."""
        if parsed_args is not None:
            return cls(**{field.name: getattr(parsed_args, field.name) for field in fields(cls)})
        return cls(**{field.name: field.default.default for field in fields(cls) if isinstance(field.default, ArgSpec)})


CONFIG = typing.TypeVar("CONFIG", bound=BaseConfig)

### in effect module


@dataclass
class Config(BaseConfig):
    subparser_data = {
        "name": "test_effect",
        "help": "help stuff",
        "description": "effect | more description",
        "epilog": "Example: stuff...",
    }

    number: int = ArgSpec(name="--number")  # type: ignore[arg-type]
    "int : positive integer"


class BaseEffect(typing.Generic[CONFIG]):
    def _get_config(self) -> type[CONFIG]:
        raise NotImplementedError

    def __init__(self) -> None:
        self.config: CONFIG = self._get_config()._build_config()


class MyEffect(BaseEffect[Config]):
    def _get_config(self) -> type[Config]:
        return Config


def get_config() -> type[Config]:
    return Config


### usage in main

# building config from args
parser = argparse.ArgumentParser()
parser.add_argument("--global", type=str)
subparsers = parser.add_subparsers(title="effects")
config_class = get_config()
config_class._populate_parser(subparsers)
args = parser.parse_args()
config = config_class._build_config(args)

# building config from spec
effect = MyEffect()
