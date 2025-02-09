"""Functions for easing calculations.

Functions:
    linear: Linear easing function.
    in_sine: Ease in using a sine function.
    out_sine: Ease out using a sine function.
    in_out_sine: Ease in/out using a sine function.
    in_quad: Ease in using a quadratic function.
    out_quad: Ease out using a quadratic function.
    in_out_quad: Ease in/out using a quadratic function.
    in_cubic: Ease in using a cubic function.
    out_cubic: Ease out using a cubic function.
    in_out_cubic: Ease in/out using a cubic function.
    in_quart: Ease in using a quartic function.
    out_quart: Ease out using a quartic function.
    in_out_quart: Ease in/out using a quartic function.
    in_quint: Ease in using a quintic function.
    out_quint: Ease out using a quintic function.
    in_out_quint: Ease in/out using a quintic function.
    in_expo: Ease in using an exponential function.
    out_expo: Ease out using an exponential function.
    in_out_expo: Ease in/out using an exponential function.
    in_circ: Ease in using a circular function.
    out_circ: Ease out using a circular function.
    in_out_circ: Ease in/out using a circular function.
    in_back: Ease in using a back function.
    out_back: Ease out using a back function.
    in_out_back: Ease in/out using a back function.
    in_elastic: Ease in using an elastic function.
    out_elastic: Ease out using an elastic function.
    in_out_elastic: Ease in/out using an elastic function.
    in_bounce: Ease in using a bounce function.
    out_bounce: Ease out using a bounce function.
    in_out_bounce: Ease in/out using a bounce function.
    eased_step_function: Create a closure that returns the eased value of each step from 0 to 1 increasing
        by the step_size.
"""

from __future__ import annotations

import functools
import math
import typing

# EasingFunction is a type alias for a function that takes a float between 0 and 1 and returns a float between 0 and 1.
EasingFunction = typing.Callable[[float], float]
"EasingFunctions take a float between 0 and 1 and return a float between 0 and 1."


def linear(progress_ratio: float) -> float:
    """Linear easing function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    return progress_ratio


def in_sine(progress_ratio: float) -> float:
    """Ease in using a sine function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    return 1 - math.cos((progress_ratio * math.pi) / 2)


def out_sine(progress_ratio: float) -> float:
    """Ease out using a sine function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    return math.sin((progress_ratio * math.pi) / 2)


def in_out_sine(progress_ratio: float) -> float:
    """Ease in/out using a sine function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    return -(math.cos(math.pi * progress_ratio) - 1) / 2


def in_quad(progress_ratio: float) -> float:
    """Ease in using a quadratic function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    return progress_ratio**2


def out_quad(progress_ratio: float) -> float:
    """Ease out using a quadratic function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    return 1 - (1 - progress_ratio) * (1 - progress_ratio)


def in_out_quad(progress_ratio: float) -> float:
    """Ease in/out using a quadratic function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    if progress_ratio < 0.5:
        return 2 * progress_ratio**2
    return 1 - (-2 * progress_ratio + 2) ** 2 / 2


def in_cubic(progress_ratio: float) -> float:
    """Ease in using a cubic function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    return progress_ratio**3


def out_cubic(progress_ratio: float) -> float:
    """Ease out using a cubic function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    return 1 - (1 - progress_ratio) ** 3


def in_out_cubic(progress_ratio: float) -> float:
    """Ease in/out using a cubic function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the
        character

    """
    if progress_ratio < 0.5:
        return 4 * progress_ratio**3
    return 1 - (-2 * progress_ratio + 2) ** 3 / 2


def in_quart(progress_ratio: float) -> float:
    """Ease in using a quartic function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 representing the percentage
        of the current waypoint speed to apply to the character

    """
    return progress_ratio**4


def out_quart(progress_ratio: float) -> float:
    """Ease out using a quartic function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    return 1 - (1 - progress_ratio) ** 4


def in_out_quart(progress_ratio: float) -> float:
    """Ease in/out using a quartic function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    if progress_ratio < 0.5:
        return 8 * progress_ratio**4
    return 1 - (-2 * progress_ratio + 2) ** 4 / 2


def in_quint(progress_ratio: float) -> float:
    """Ease in using a quintic function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    return progress_ratio**5


def out_quint(progress_ratio: float) -> float:
    """Ease out using a quintic function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    return 1 - (1 - progress_ratio) ** 5


def in_out_quint(progress_ratio: float) -> float:
    """Ease in/out using a quintic function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    if progress_ratio < 0.5:
        return 16 * progress_ratio**5
    return 1 - (-2 * progress_ratio + 2) ** 5 / 2


def in_expo(progress_ratio: float) -> float:
    """Ease in using an exponential function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    if progress_ratio == 0:
        return 0
    return 2 ** (10 * progress_ratio - 10)


def out_expo(progress_ratio: float) -> float:
    """Ease out using an exponential function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    if progress_ratio == 1:
        return 1
    return 1 - 2 ** (-10 * progress_ratio)


def in_out_expo(progress_ratio: float) -> float:
    """Ease in/out using an exponential function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    if progress_ratio == 0:
        return 0
    if progress_ratio == 1:
        return 1
    if progress_ratio < 0.5:
        return 2 ** (20 * progress_ratio - 10) / 2
    return (2 - 2 ** (-20 * progress_ratio + 10)) / 2


def in_circ(progress_ratio: float) -> float:
    """Ease in using a circular function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    return 1 - math.sqrt(1 - progress_ratio**2)


def out_circ(progress_ratio: float) -> float:
    """Ease out using a circular function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    return math.sqrt(1 - (progress_ratio - 1) ** 2)


def in_out_circ(progress_ratio: float) -> float:
    """Ease in/out using a circular function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    if progress_ratio < 0.5:
        return (1 - math.sqrt(1 - (2 * progress_ratio) ** 2)) / 2
    return (math.sqrt(1 - (-2 * progress_ratio + 2) ** 2) + 1) / 2


def in_back(progress_ratio: float) -> float:
    """Ease in using a back function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    c1 = 1.70158
    c3 = c1 + 1
    return c3 * progress_ratio**3 - c1 * progress_ratio**2


def out_back(progress_ratio: float) -> float:
    """Ease out using a back function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (progress_ratio - 1) ** 3 + c1 * (progress_ratio - 1) ** 2


def in_out_back(progress_ratio: float) -> float:
    """Ease in/out using a back function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    c1 = 1.70158
    c2 = c1 * 1.525
    if progress_ratio < 0.5:
        return ((2 * progress_ratio) ** 2 * ((c2 + 1) * 2 * progress_ratio - c2)) / 2
    return ((2 * progress_ratio - 2) ** 2 * ((c2 + 1) * (progress_ratio * 2 - 2) + c2) + 2) / 2


def in_elastic(progress_ratio: float) -> float:
    """Ease in using an elastic function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    c4 = (2 * math.pi) / 3
    if progress_ratio == 0:
        return 0
    if progress_ratio == 1:
        return 1
    return -(2 ** (10 * progress_ratio - 10)) * math.sin((progress_ratio * 10 - 10.75) * c4)


def out_elastic(progress_ratio: float) -> float:
    """Ease out using an elastic function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character

    """
    c4 = (2 * math.pi) / 3
    if progress_ratio == 0:
        return 0
    if progress_ratio == 1:
        return 1
    return 2 ** (-10 * progress_ratio) * math.sin((progress_ratio * 10 - 0.75) * c4) + 1


def in_out_elastic(progress_ratio: float) -> float:
    """Ease in/out using an elastic function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character

    """
    c5 = (2 * math.pi) / 4.5
    if progress_ratio == 0:
        return 0
    if progress_ratio == 1:
        return 1
    if progress_ratio < 0.5:
        return -(2 ** (20 * progress_ratio - 10) * math.sin((20 * progress_ratio - 11.125) * c5)) / 2
    return (2 ** (-20 * progress_ratio + 10) * math.sin((20 * progress_ratio - 11.125) * c5)) / 2 + 1


def in_bounce(progress_ratio: float) -> float:
    """Ease in using a bounce function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character

    """
    return 1 - out_bounce(1 - progress_ratio)


def out_bounce(progress_ratio: float) -> float:
    """Ease out using a bounce function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    n1 = 7.5625
    d1 = 2.75
    if progress_ratio < 1 / d1:
        return n1 * progress_ratio**2
    if progress_ratio < 2 / d1:
        return n1 * (progress_ratio - 1.5 / d1) ** 2 + 0.75
    if progress_ratio < 2.5 / d1:
        return n1 * (progress_ratio - 2.25 / d1) ** 2 + 0.9375
    return n1 * (progress_ratio - 2.625 / d1) ** 2 + 0.984375


def in_out_bounce(progress_ratio: float) -> float:
    """Ease in/out using a bounce function.

    Args:
        progress_ratio (float): the ratio of the current step to the maximum steps

    Returns:
        float: 0 <= n <= 1 eased value

    """
    if progress_ratio < 0.5:
        return (1 - out_bounce(1 - 2 * progress_ratio)) / 2
    return (1 + out_bounce(2 * progress_ratio - 1)) / 2


def make_easing(x1: float, y1: float, x2: float, y2: float) -> EasingFunction:
    """Create a cubic Bezier easing function using the provided control points.

    The easing function maps an input progress ratio (0 to 1) to an output value (0 to 1)
    according to a cubic Bezier curve defined by four points:
      - Start point: (0, 0)
      - First control point: (x1, y1)
      - Second control point: (x2, y2)
      - End point: (1, 1)

    Args:
      x1 (float): Determines the horizontal position of the first control point. Smaller values make the
          curve start off steeper, while larger values delay the initial acceleration.
      y1 (float): Determines the vertical position of the first control point. Smaller values create a
          gentler ease-in effect; larger values increase the initial acceleration.
      x2 (float): Determines the horizontal position of the second control point. Larger values extend
          the period of change, affecting how late the acceleration or deceleration begins.
      y2 (float): Determines the vertical position of the second control point. Larger values can create a
          more abrupt ease-out effect; smaller values result in a smoother finish.

    Note: Use a resource such as cubic-bezier.com to design an appropriate easing curve for your needs.

    Returns:
        EasingFunction: A function that takes a progress_ratio (0 <= progress_ratio <= 1) and returns
        the eased value computed from the cubic Bezier curve.

    """

    # Compute Bezier curve x for a given parameter t.
    def sample_curve_x(t: float) -> float:
        return 3 * x1 * (1 - t) ** 2 * t + 3 * x2 * (1 - t) * t**2 + t**3

    # Compute Bezier curve y for a given parameter t.
    def sample_curve_y(t: float) -> float:
        return 3 * y1 * (1 - t) ** 2 * t + 3 * y2 * (1 - t) * t**2 + t**3

    # Compute derivative of curve x with respect to t.
    def sample_curve_derivative_x(t: float) -> float:
        return 3 * (1 - t) ** 2 * x1 + 6 * (1 - t) * t * (x2 - x1) + 3 * t**2 * (1 - x2)

    def bezier_easing(progress: float) -> float:
        # Clamp progress between 0 and 1.
        if progress <= 0:
            return 0
        if progress >= 1:
            return 1

        # Find t such that sample_curve_x(t) is close to progress.
        t = progress  # initial guess
        for _ in range(20):
            x_est = sample_curve_x(t)
            dx = x_est - progress
            if abs(dx) < 1e-5:
                break
            d = sample_curve_derivative_x(t)
            if abs(d) < 1e-6:
                break
            t -= dx / d
        return sample_curve_y(t)

    return functools.wraps(bezier_easing)(functools.lru_cache(maxsize=8192)(bezier_easing))


make_easing = functools.wraps(make_easing)(functools.lru_cache(maxsize=8192)(make_easing))


def eased_step_function(
    easing_func: EasingFunction,
    step_size: float,
    *,
    clamp: bool = False,
) -> typing.Callable[[], tuple[float, float]]:
    """Create a closure that returns the eased value of each step from 0 to 1 increasing by the step_size.

    Args:
        easing_func (EasingFunction): The easing function to use.
        step_size (float): The step size.
        clamp (bool): If True, the easing function will be limited to 0 <= n <= 1. Defaults to False.

    Returns:
        callable[[],tuple[float,float]]: A closure that returns a tuple of the current input step and eased value of
        the current input step.

    """
    if not 0 < step_size <= 1:
        msg = "Step size must be 0 < n <= 1."
        raise ValueError(msg)

    current_step = 0.0

    def ease() -> tuple[float, float]:
        nonlocal current_step
        eased_value = easing_func(current_step)
        used_step = current_step
        if current_step < 1:
            current_step = min((current_step + step_size, 1.0))
        if clamp:
            eased_value = max(0, min(eased_value, 1))
        return used_step, eased_value

    return ease
