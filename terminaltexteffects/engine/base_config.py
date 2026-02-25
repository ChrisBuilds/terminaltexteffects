"""Base effect configuration classes.

`BaseConfig` works with `argutils.ArgSpec` field defaults to define effect
configuration options and populate an `argparse.ArgumentParser`.

`BaseConfig._build_config` constructs config instances either from a parsed
`argparse.Namespace` or from the default values stored on each field's
`ArgSpec`.
"""

from __future__ import annotations

import argparse
import typing
from dataclasses import dataclass, fields

from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.graphics import Color, Gradient


@dataclass(frozen=True)
class FinalGradientDirectionArg(argutils.ArgSpec):
    """Argument specification for selecting the final text gradient direction."""

    name: str = "--final-gradient-direction"
    type: typing.Callable[[str], Gradient.Direction] = argutils.GradientDirection.type_parser
    default: Gradient.Direction = Gradient.Direction.VERTICAL
    metavar: str = argutils.GradientDirection.METAVAR
    help: str = "Direction of the final gradient across the text."


@dataclass(frozen=True)
class FinalGradientStopsArg(argutils.ArgSpec):
    """Argument specification for selecting the final text gradient stops."""

    name: str = "--final-gradient-stops"
    type: typing.Callable[[str], Color] = argutils.ColorArg.type_parser
    nargs: str = "+"
    action: type[argutils.TupleAction] = argutils.TupleAction
    default: tuple[Color, ...] = (Color("#8A008A"), Color("#00D1FF"), Color("#FFFFFF"))
    metavar: str = argutils.ColorArg.METAVAR
    help: str = (
        "Space separated, unquoted, list of colors for the character gradient (applied across the canvas). "
        "If only one color is provided, the characters will be displayed in that color."
    )


@dataclass(frozen=True)
class FinalGradientStepsArg(argutils.ArgSpec):
    """Argument specification for selecting the final text gradient steps."""

    name: str = "--final-gradient-steps"
    type: typing.Callable[[str], int] = argutils.PositiveInt.type_parser
    nargs: str = "+"
    action: type[argutils.TupleAction] = argutils.TupleAction
    default: tuple[int, ...] | int = 12
    metavar: str = argutils.PositiveInt.METAVAR
    help: str = (
        "Space separated, unquoted, list of the number of gradient steps to use. "
        "More steps will create a smoother and longer gradient animation."
    )


@dataclass(frozen=True)
class FinalGradientFramesArg(argutils.ArgSpec):
    """Argument specification for selecting the final text gradient frames."""

    name: str = "--final-gradient-frames"
    type: typing.Callable[[str], int] = argutils.PositiveInt.type_parser
    default: int = 5
    metavar: str = argutils.PositiveInt.METAVAR
    help: str = "Number of frames to display each gradient step. Increase to slow down the gradient animation."


@dataclass
class BaseConfig:
    """Base configuration class for effects.

    This class serves as a base for all effect configurations, providing a common
    interface for argument parser population and configuration building. Effect config classes
    are created via `_build_config`, which can read values from a parsed
    `argparse.Namespace` or from each field's `argutils.ArgSpec` defaults. Any
    config class intended to be used to populate a subparser must define a
    `parser_spec` attribute with type `argutils.ParserSpec`.
    """

    @classmethod
    def _populate_parser(cls, parser: argparse.ArgumentParser | argparse._SubParsersAction) -> None:
        """Populate the argument parser with the effect's configuration options.

        If a subparser is being populated, `cls.parser_spec` is used to create
        the subparser before adding the class field argument specs.
        """
        if isinstance(parser, argparse._SubParsersAction):
            parser = parser.add_parser(**vars(cls.parser_spec))  # pyright: ignore[reportAttributeAccessIssue]
            parser.formatter_class = argutils.CustomFormatter  # pyright: ignore[reportAttributeAccessIssue]

        assert isinstance(parser, argparse.ArgumentParser)
        for field in fields(cls):
            if field.name == "parser_spec":
                continue
            spec = field.default
            assert isinstance(spec, argutils.ArgSpec)
            add_args_sig = {k: v for k, v in vars(spec).items() if v is not argutils._MISSING}
            parser.add_argument(add_args_sig.pop("name"), **add_args_sig)

    @classmethod
    def _build_config(cls: type[CONFIG], parsed_args: argparse.Namespace | None = None) -> CONFIG:
        """Build a config instance from a parsed namespace or `ArgSpec` defaults."""
        if parsed_args is not None:
            config_args: dict[str, typing.Any] = {}
            for field in fields(cls):
                if field.name == "parser_spec":
                    continue
                if hasattr(parsed_args, field.name):
                    config_args[field.name] = getattr(parsed_args, field.name)
                elif isinstance(field.default, argutils.ArgSpec):
                    config_args[field.name] = field.default.default
                else:
                    msg = f"Missing required config field '{field.name}' for {cls.__name__} in parsed arguments."
                    raise AttributeError(msg)
            return cls(**config_args)
        return cls(
            **{
                field.name: field.default.default
                for field in fields(cls)
                if isinstance(field.default, argutils.ArgSpec)
            },
        )


CONFIG = typing.TypeVar("CONFIG", bound=BaseConfig)
