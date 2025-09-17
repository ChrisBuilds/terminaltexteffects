# ColorPair

*Module*: `terminaltexteffects.utils.graphics`

## Basic Usage

ColorPair objects are used to represent a foreground and background color pair.

### Usage

```python
import terminaltexteffects as tte

color_pair = tte.ColorPair(fg=tte.Color("#FF0000"), bg=tte.Color("#00FF00"))
```

### Alternate Signature

Colors can be specified using strings or integers. Color objects will be created automatically.

```python
import terminaltexteffects as tte

color_pair = tte.ColorPair("#FF0000", "#00FF00")
```

`fg` and/or `bg` are optional and default to `None`.

### Printing ColorPairs

ColorPair objects can be printed to see the resulting colors.

![t](../../img/lib_demos/colorpair_print_example.png)

---

## ColorPair Reference

::: terminaltexteffects.utils.graphics.ColorPair
