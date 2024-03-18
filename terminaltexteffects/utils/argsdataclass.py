import argparse
import inspect
import typing
from dataclasses import MISSING, Field, dataclass, fields


class ArgField(Field):
    """
    A subclass of the dataclasses.Field class that represents a command-line argument.

    This class extends the built-in Field class to include additional metadata specific to command-line arguments.
    This metadata includes the command-line argument name, help text, type parser, metavar, nargs, action, required
    status, and choices.

    The class also overrides the __init__ method to handle the additional metadata and to set default values based on
    the 'action' attribute. If 'action' is "store_true", the default value is set to False. If 'action' is "store_false",
    the default value is set to True.

    Args:
        cmd_name (str | list[str]): The name or names of the command-line argument.
        help (str): The help text to display for the argument.
        type_parser (typing.Any, optional): The validator to use to validate the argument. Defaults to None.
        metavar (str | None, optional): A name for the argument in usage messages. Defaults to None.
        nargs (str | None, optional): The number of command-line arguments that should be consumed. Defaults to None.
        action (str | None, optional): The basic type of action to be taken when this argument is encountered at the
                                       command line. Defaults to None.
        required (bool, optional): Whether or not the command-line option is required. Defaults to False.
        choices (list[str | int] | None, optional): A container of the allowable values for the argument. Defaults to None.
        default (any, optional): The value produced if the argument is absent from the command line. Defaults to MISSING.
        default_factory (any, optional): A function that is called to provide the default value. Defaults to MISSING.
        init (bool, optional): If true (the default), this field is included as a parameter to the generated __init__
                               method. Defaults to True.
        repr (bool, optional): If true (the default), this field is included in the string returned by the generated
                               __repr__ method. Defaults to True.
        hash (bool | None, optional): This can be a bool or None. If true, this field is included in the generated
                                      __hash__ method. Defaults to None.
        compare (bool, optional): If true (the default), this field is included in the generated equality and comparison
                                  methods (__eq__, __gt__, etc.). Defaults to True.
        kw_only (bool, optional): If true, this field must be passed as a keyword argument. Defaults to MISSING.
    """

    def __init__(
        self,
        # custom metadata
        cmd_name: str | list[str],
        help: str,
        type_parser: typing.Callable | None = None,
        metavar: str | None = None,
        nargs: str | None = None,
        action: str | None = None,
        required: bool = False,
        choices: list[str | int] | None = None,
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
            choices=choices,
        )
        if action == "store_true":
            default = False
        elif action == "store_false":
            default = True

        super().__init__(default, default_factory, init, repr, hash, compare, vars(additional_metadata), kw_only)

    @dataclass
    class FieldAdditionalMetaData:
        cmd_name: str | list[str]
        type_parser: typing.Any | None = None
        metavar: str | None = None
        nargs: str | None = None
        help: str | None = None
        action: str | None = None
        required: bool = False
        choices: list[str | int] | None = None


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
    """
    A dataclass that represents command-line arguments and provides methods for handling them.

    This class provides a structured way to define and work with command-line arguments. It uses Python's built-in
    dataclasses and the argparse module to parse command-line arguments and create an instance of the class from them.

    Note:
        This class does not define any fields itself. Instead, it is meant to be subclassed, with subclasses defining
        their own fields to represent the command-line arguments they expect.
    """

    @classmethod
    def from_parsed_args_mapping(cls, parsed_args: argparse.Namespace, arg_class=None):
        """
        Creates an instance of the ArgsDataClass from parsed command-line arguments.

        This method takes a Namespace object, which is the result of parsing command-line arguments with argparse, and an
        optional class to instantiate. If no class is provided, it uses the 'arg_class' attribute from the parsed_args.

        It retrieves the signature of the __init__ method of the target class and iterates over its parameters. For each
        parameter, it gets the corresponding value from the parsed_args. If the value is a list (which can happen if the
        argument was defined with nargs="+" or nargs="*"), it converts the list to a tuple.

        It then creates a new instance of the target class, passing the collected parameters as keyword arguments.

        Args:
            parsed_args (argparse.Namespace): The parsed command-line arguments.
            arg_class (Optional[Type]): The class to instantiate. If None, uses 'arg_class' attribute from parsed_args.

        Returns:
            An instance of the target class, initialized with values from the parsed_args.

        Note:
            This method assumes that the names of the command-line arguments match the parameter names of the target class's
            __init__ method. If this is not the case, it may not work as expected.
        """
        if arg_class is None:
            arg_class = parsed_args.arg_class

        signature = inspect.signature(arg_class.__init__)
        parameters = signature.parameters
        params_dict = {}
        for param in parameters:
            if param == "self":
                continue
            param_value = getattr(parsed_args, param)
            if isinstance(param_value, list):  # argparser returns list for nargs="+" or nargs="*"
                param_value = tuple(param_value)
            params_dict[param] = param_value

        new_instance = arg_class(**params_dict)
        return new_instance

    @classmethod
    def get_all_fields(cls) -> dict[str, Field]:
        """
        Retrieves all fields defined in the ArgsDataClass and returns them as a dictionary.

        This method uses the `fields` function from the `dataclasses` module to get a list of all fields defined in the
        ArgsDataClass. It then iterates over these fields, adding each one to a dictionary with the field's name as the key
        and the field itself as the value.

        Returns:
            dict[str, Field]: A dictionary mapping field names to their corresponding Field objects. Each Field object
                            contains information about the field, such as its name, type, and any default values or
                            metadata it may have.
        """
        fields_list = {}
        for f in fields(cls):
            fields_list[f.name] = f

        return fields_list

    @classmethod
    def add_args_to_parser(cls, parser: argparse.ArgumentParser):
        """
        Adds arguments to the provided parser based on the fields defined in the ArgsDataClass.

        This method iterates over all fields in the ArgsDataClass. For each field, it checks if it has metadata.
        If metadata is present, it creates an instance of FieldAdditionalMetaData using the metadata.
        It then prepares a dictionary of argument descriptors, mapping field names to their corresponding values.
        These descriptors are used to add an argument to the parser with the `add_argument` method.

        Args:
            parser (argparse.ArgumentParser): The parser to which arguments will be added. Each argument corresponds
                                            to a field in the ArgsDataClass, and the argument's properties are
                                            determined by the field's metadata.

        Note:
            The 'type_parser' field name is specially handled and mapped to 'type' in the argument descriptors.
            The 'cmd_name' field is used as the name of the argument added to the parser. If 'cmd_name' is a string,
            it is wrapped in a list before being passed to `add_argument`.
            If a field has no metadata, it is skipped and no corresponding argument is added to the parser.
        """
        arg_fields = cls.get_all_fields()
        for arg in arg_fields.values():
            if not arg.metadata:
                continue
            additional_metadata = ArgField.FieldAdditionalMetaData(**arg.metadata)
            if isinstance(additional_metadata.cmd_name, str):
                additional_metadata.cmd_name = [additional_metadata.cmd_name]
            field_names_mapping = {"type_parser": "type"}
            arg_descriptor = {}
            for attr_name in vars(additional_metadata):
                value = getattr(additional_metadata, attr_name)
                if value is None:
                    continue
                if attr_name == "cmd_name":
                    continue
                if attr_name in field_names_mapping:
                    attr_name = field_names_mapping[attr_name]

                arg_descriptor[attr_name] = value

            parser.add_argument(*additional_metadata.cmd_name, **arg_descriptor, default=arg.default)

    @classmethod
    def add_to_args_subparsers(cls, subparsers: argparse._SubParsersAction):
        """Adds arguments to the subparser.

        Args:
            arg_data_class (ArgsDataClass): ArgDataClass that required args defined in it
            subparser (argparse._SubParsersAction): subparser to add arguments to
        """
        sub_parser_descriptor = getattr(cls, "arg_class_metadata")
        new_parser = subparsers.add_parser(**vars(sub_parser_descriptor))
        new_parser.set_defaults(arg_class=cls)
        cls.add_args_to_parser(new_parser)


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
