from __future__ import annotations
from dataclasses import dataclass, fields
import argparse
import typing

MISSING = object()

#### demo validator


class PositiveInt:
    METAVAR = "(int > 0)"

    @staticmethod
    def validator(arg: str) -> int:
        try:
            arg_int = int(arg)
        except ValueError:
            raise argparse.ArgumentTypeError
        if arg_int <= 0:
            raise argparse.ArgumentTypeError
        return arg_int


#### in base_config


@dataclass(frozen=True)
class ArgSpec:
    name: str
    metavar: str = MISSING  # type: ignore[arg-type]
    type: typing.Any = MISSING  # type: ignore[arg-type]
    default: bool | int = MISSING  # type: ignore[arg-type]
    required: bool = MISSING  # type: ignore[arg-type]
    help: str = MISSING  # type: ignore[arg-type]


@dataclass
class BaseConfig:
    subparser_data: typing.ClassVar[dict[str, str]]

    @classmethod
    def populate_parser(cls, parser: argparse.ArgumentParser | argparse._SubParsersAction) -> None:
        if isinstance(parser, argparse._SubParsersAction):
            parser = parser.add_parser(**cls.subparser_data)  # type: ignore[arg-type]

        assert isinstance(parser, argparse.ArgumentParser)
        for field in fields(cls):
            spec = field.default
            assert isinstance(spec, ArgSpec)
            add_args_sig = {k: v for k, v in vars(spec).items() if v is not MISSING}
            parser.add_argument(add_args_sig.pop("name"), **add_args_sig)

    @classmethod
    def from_parsed_args(cls, parsed_args: argparse.Namespace) -> BaseConfig:
        return cls(**{field.name: getattr(parsed_args, field.name) for field in fields(cls)})


### in effect module


@dataclass
class Config(BaseConfig):
    subparser_data = {
        "name": "test_effect",
        "help": "help stuff",
        "description": "effect | more description",
        "epilog": "Example: stuff...",
    }

    number: int = ArgSpec(name="--number", metavar=PositiveInt.METAVAR, type=PositiveInt.validator)  # type: ignore[arg-type]
    "int : positive integer"


def get_config() -> type[Config]:
    return Config


### usage in main

parser = argparse.ArgumentParser()
parser.add_argument("--global", type=str)
subparsers = parser.add_subparsers(title="effects")
config_class = get_config()
config_class.populate_parser(subparsers)
args = parser.parse_args()

config = config_class.from_parsed_args(args)
