import argparse
import inspect
from dataclasses import Field, dataclass, fields, MISSING
import typing


class ArgField(Field):
    def __init__(
        self,
        # custom metadata
        cmd_name: str | list[str],
        help: str,
        type_parser: typing.Any = None,
        metavar: str|None = None,
        nargs: str|None = None,
        action: str|None = None,
        required: bool = False,
        # python internal attrs
        default=MISSING,
        default_factory=MISSING,
        init=True,
        repr=True,
        hash=None,
        compare=True,
        kw_only=MISSING,
    ):
        additional_metadata = ArgField.FieldAdditionalMetaData(
            cmd_name=cmd_name,
            type_parser=type_parser,
            metavar=metavar,
            nargs=nargs,
            help=help,
            action=action,
            required=required,
        )

        super().__init__(default, default_factory, init, repr, hash, compare, vars(additional_metadata), kw_only)

    @dataclass
    class FieldAdditionalMetaData:
        cmd_name: str | list[str]
        type_parser: typing.Any|None = None
        metavar: str|None = None
        nargs: str|None = None
        help: str|None = None
        action: str|None = None
        required: bool = False
        
        
@dataclass
class ArgParserDescriptor:
    """This dataclass contains required attributes to call "add_parser()" method of
    _argparse._SubParsersAction" class
    """
    name: str
    formatter_class: typing.Any
    help: str
    description: str
    epilog: str        


@dataclass
class ArgsDataClass:
    @classmethod
    def from_parsed_args_mapping(selfClass, parsed_args: argparse.Namespace, arg_class=None):
        # parsed_args.
        if arg_class is None:
            arg_class= parsed_args.arg_class

        signature = inspect.signature(arg_class.__init__)
        parameters = signature.parameters
        params_dict = {}
        for param in parameters:
            if param == "self":
                continue
            params_dict[param] = getattr(parsed_args, param)

        new_instance = arg_class(**params_dict)
        return new_instance

    @classmethod
    def get_All_fields(selfClass) -> dict[str, Field]:
        fields_list = {}
        for f in fields(selfClass):
            fields_list[f.name] = f

        return fields_list

    @classmethod
    def add_args_to_parser(selfClass, parser):
        args = selfClass.get_All_fields()
        for arg in args.values():
            if not arg.metadata:
                continue
            additional_metadata = ArgField.FieldAdditionalMetaData(**arg.metadata)
            if isinstance(additional_metadata.cmd_name, str):
                additional_metadata.cmd_name = [additional_metadata.cmd_name]
            field_names_mapping= {"type_parser":"type"}
            arg_descriptor = {}
            for attr_name in vars(additional_metadata):
                value = getattr(additional_metadata, attr_name)
                if value is None:
                    continue
                if attr_name == "cmd_name":
                    continue
                if attr_name in field_names_mapping:
                    attr_name= field_names_mapping[attr_name]
                    
                arg_descriptor[attr_name] = value

            parser.add_argument(*additional_metadata.cmd_name, **arg_descriptor, default=arg.default)

    @classmethod
    def add_to_args_subparsers(selfClass, subparsers: argparse._SubParsersAction):
        """Adds arguments to the subparser.

        Args:
            arg_data_class (ArgsDataClass): ArgDataClass that required args defined in it
            subparser (argparse._SubParsersAction): subparser to add arguments to
        """
        sub_parser_descriptor= getattr(selfClass,"arg_class_metadata")
        new_parser = subparsers.add_parser(**vars(sub_parser_descriptor))
        new_parser.set_defaults(arg_class=selfClass)
        selfClass.add_args_to_parser(new_parser)
        
    #arg_class_metadata:ArgParserDescriptor|None= None


def argclass(name: str, formatter_class: typing.Any, help: str, description: str, epilog: str):
    """Decorator for providing required metadata to an "ArgDataClass"

    Args:
        name (str): name for parser or subparser
        formatter_class (any): formatter function for parser or subparser
        help (str): help string for parser or subparser
        description (str): description string for parser or subparser
        epilog (str): epilog string for parser or subparser
    """
    def decorator(cls):
        cls.arg_class_metadata = ArgParserDescriptor(
            name=name, formatter_class=formatter_class, help=help, description=description, epilog=epilog
        )
        return cls

    return decorator
