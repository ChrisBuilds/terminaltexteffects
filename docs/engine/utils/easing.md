# Easing Functions

*Module*: `terminaltexteffects.utils.easing`

Easing functions take a progress ratio from 0 to 1. Back and elastic functions
can return values below 0 or above 1. Custom curves from `make_easing` can also
overshoot when their vertical control points are outside `[0, 1]`. The horizontal
control points, `x1` and `x2`, must be finite values in `[0, 1]`.

`EasingTracker` preserves overshoot by default; pass `clamp=True` to limit its
stepped values to `[0, 1]`. `SequenceEaser` always clamps its internal tracker
before selecting elements.

```python
from terminaltexteffects.utils import easing

assert easing.in_back(0.5) < 0
assert easing.out_elastic(0.5) > 1

tracker = easing.EasingTracker(lambda _: 1.25, total_steps=1, clamp=True)
assert tracker.step() == 1.0
```

::: terminaltexteffects.utils.easing
