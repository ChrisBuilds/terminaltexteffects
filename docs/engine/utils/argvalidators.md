# Argument Validation

*Module*: `terminaltexteffects.utils.argutils`

::: terminaltexteffects.utils.argutils

## Example Usage

The following example demonstrates using the `PositiveFloat` class to provide a `type_parser` and `metavar` to the `RandomSequenceConfig.speed` argument. This will validate that the argument passed as `--speed` is a float > 0.

```python
class RandomSequenceConfig(ArgsDataClass):
    speed: float = ArgField(
        cmd_name=["--speed"],
        type_parser=argutils.PositiveFloat.type_parser,
        default=0.004,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Speed of the animation as a percentage of the total number of characters to reveal in each tick.",
    )  # type: ignore[assignment]

```
