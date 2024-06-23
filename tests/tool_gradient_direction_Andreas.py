import argparse

from terminaltexteffects.utils.graphics import Gradient

# Initialize coverage tracking global variable
branch_coverage = {
    "type_parser_valid_horizontal": False,
    "type_parser_valid_vertical": False,
    "type_parser_valid_diagonal": False,
    "type_parser_valid_radial": False,
    "type_parser_invalid": False,
}

class GradientDirection:
    """Argument type for gradient directions.

    Raises:
        argparse.ArgumentTypeError: Argument value is not a valid gradient direction.
    """

    METAVAR = "(diagonal, horizontal, vertical, radial)"

    @staticmethod
    def type_parser(arg: str) -> Gradient.Direction:
        """Validates that the given argument is a valid gradient direction.

        Args:
            arg (str): argument to validate

        Returns:
            Gradient.Direction: validated gradient direction

        Raises:
            argparse.ArgumentTypeError: Argument value is not a valid gradient direction.
        """
        direction_map = {
            "horizontal": Gradient.Direction.HORIZONTAL,
            "vertical": Gradient.Direction.VERTICAL,
            "diagonal": Gradient.Direction.DIAGONAL,
            "radial": Gradient.Direction.RADIAL,
        }
        if arg.lower() in direction_map:
            if arg.lower() == "horizontal":
                branch_coverage["type_parser_valid_horizontal"] = True
            elif arg.lower() == "vertical":
                branch_coverage["type_parser_valid_vertical"] = True
            elif arg.lower() == "diagonal":
                branch_coverage["type_parser_valid_diagonal"] = True
            elif arg.lower() == "radial":
                branch_coverage["type_parser_valid_radial"] = True
            return direction_map[arg.lower()]
        else:
            branch_coverage["type_parser_invalid"] = True
            raise argparse.ArgumentTypeError(
                f"invalid gradient direction: '{arg}' is not a valid gradient direction. Choices are diagonal, horizontal, vertical, or radial."
            )

def print_coverage():
    total_branches = len(branch_coverage)
    hit_branches = sum(hit for hit in branch_coverage.values())
    coverage_percentage = (hit_branches / total_branches) * 100
    for branch, hit in branch_coverage.items():
        print(f"{branch} was {'hit' if hit else 'not hit'}")
    print(f"Coverage: {coverage_percentage:.2f}%")

def main():
    # Example 
    try:
        result = GradientDirection.type_parser("horizontal")
    except argparse.ArgumentTypeError:
        pass
    

    try:
        result = GradientDirection.type_parser("vertical")
    except argparse.ArgumentTypeError:
        pass
  

    try:
        result = GradientDirection.type_parser("diagonal")
    except argparse.ArgumentTypeError:
        pass
    

    try:
        result = GradientDirection.type_parser("radial")
    except argparse.ArgumentTypeError:
        pass
    

    try:
        result = GradientDirection.type_parser("invalid_direction")
    except argparse.ArgumentTypeError:
        pass
    print_coverage()

if __name__ == "__main__":
    main()