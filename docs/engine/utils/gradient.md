# Gradient

*Module*: `terminaltexteffects.utils.graphics`

## Basic Usage

```python
from terminaltexteffects.utils.graphics import Gradient, Color

rgb = Gradient(Color("ff0000"), Color("00ff00"), Color("0000ff"), steps=5)
for color in rgb:
    # color is a hex string
    ...
```

::: terminaltexteffects.utils.graphics.Gradient
