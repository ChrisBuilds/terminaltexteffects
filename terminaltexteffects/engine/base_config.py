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

from terminaltexteffects.utils.argutils import _MISSING, ArgSpec, CustomFormatter


@dataclass
class BaseConfig:
    """Base configuration class for effects.

    This class serves as a base for all effect configurations, providing a common
    interface for argument parsing and configuration building. All sub-classes
    must implement the `_get_config` method to return their specific configuration
    class. Any config class intended to be used to populate a subparser must
    define a `parser_spec` attribute with type `argutils.ParserSpec`.
    """

    @classmethod
    def _populate_parser(cls, parser: argparse.ArgumentParser | argparse._SubParsersAction) -> None:
        """Populate the argument parser with the effect's configuration options.

        If a subparser is being populated, the subparser_data will be used to
        configure the subparser defaults.
        """
        if isinstance(parser, argparse._SubParsersAction):
            parser = parser.add_parser(**vars(cls.parser_spec))  # pyright: ignore[reportAttributeAccessIssue]
            parser.formatter_class = CustomFormatter  # pyright: ignore[reportAttributeAccessIssue]

        assert isinstance(parser, argparse.ArgumentParser)
        for field in fields(cls):
            if field.name == "parser_spec":
                continue
            spec = field.default
            assert isinstance(spec, ArgSpec)
            add_args_sig = {k: v for k, v in vars(spec).items() if v is not _MISSING}
            parser.add_argument(add_args_sig.pop("name"), **add_args_sig)

    @classmethod
    def _build_config(cls: type[CONFIG], parsed_args: argparse.Namespace | None = None) -> CONFIG:
        """Build the effect configuration from the parsed arguments or argument specifications."""
        if parsed_args is not None:
            return cls(
                **{
                    field.name: getattr(parsed_args, field.name) for field in fields(cls) if field.name != "parser_spec"
                },
            )
        return cls(**{field.name: field.default.default for field in fields(cls) if isinstance(field.default, ArgSpec)})


CONFIG = typing.TypeVar("CONFIG", bound=BaseConfig)
