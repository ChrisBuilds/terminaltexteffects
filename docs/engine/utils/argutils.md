# ArgUtils

*Module*: `terminaltexteffects.utils.argutils`

::: terminaltexteffects.utils.argutils

## Example Usage

The `RandomSequenceConfig.speed` option uses `ArgSpec` with `PositiveFloat.type_parser`
to require a value greater than zero. This minimal config follows the same declaration
pattern and works with both direct construction and CLI parsing:

```python
import argparse
from dataclasses import dataclass

from terminaltexteffects.engine.base_config import BaseConfig
from terminaltexteffects.utils import argutils


@dataclass
class SpeedConfig(BaseConfig):
    parser_spec: argutils.ParserSpec = argutils.ParserSpec(
        name="speed-example",
        help="Show the speed option.",
        description="Example speed configuration.",
        epilog="",
    )
    speed: float = argutils.ArgSpec(
        name="--speed",
        type=argutils.PositiveFloat.type_parser,
        default=0.007,
        metavar=argutils.PositiveFloat.METAVAR,
        help="Speed of the animation.",
    )  # pyright: ignore[reportAssignmentType]


assert SpeedConfig(speed="0.01").speed == 0.01

parser = argparse.ArgumentParser()
SpeedConfig._populate_parser(parser)
config = SpeedConfig._build_config(parser.parse_args(["--speed", "0.01"]))
assert config.speed == 0.01
```

```
