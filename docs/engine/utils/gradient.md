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

## Printing Gradients

Gradients can be printed to the terminal to show information about the stops, steps, and resulting spectrum.

![t](../../img/lib_demos/printing_gradients_demo.png)

---

## Gradient Reference

::: terminaltexteffects.utils.graphics.Gradient
