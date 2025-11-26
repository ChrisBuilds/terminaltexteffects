"""Functions and Classes for easing calculations.

Classes:
    EasingTracker: Tracks the progression of an easing function over a set number of steps.
    SequenceEaser: Eases over a sequence, tracking added, removed, and total elements

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
    make_easing: Create a cubic Bezier easing function using the provided control points.
"""

from __future__ import annotations

import functools
import math
import typing
from dataclasses import InitVar, dataclass, field

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


@dataclass
class EasingTracker:
    """Describe the progression of items as an easing function is applied over a sequence.

    Attributes:
        easing_function (EasingFunction): The easing function being tracked.
        total_steps (int): The total number of steps for the easing function.
        current_step (int): The current step in the easing progression.
        progress_ratio (float): The ratio of the current step to the total steps.
        step_delta (float): The change in eased value from the last step to the current step.
        eased_value (float): The current eased value based on the easing function and progress ratio.

    Methods:
        step() -> float: Advance the easing tracker by one step and return the new eased value.
        is_complete() -> bool: Check if the easing tracker has completed all steps.

    """

    easing_function: EasingFunction
    total_steps: int = 100
    clamp: InitVar[bool] = field(default=False)

    def __post_init__(self, clamp: bool) -> None:
        """Initialize the EasingTracker.

        Args:
            clamp (bool, optional): If True, clamp the eased value between 0 and 1. Defaults to False.

        """
        self._clamp = clamp
        self.current_step: int = 0
        self.progress_ratio: float = 0.0
        self.step_delta: float = 0.0
        self.eased_value: float = 0.0
        self._last_eased_value: float = 0.0

    def step(self) -> float:
        """Advance the easing tracker by one step.

        If the current step is less than the total steps, increment the current step,
        update the progress ratio, compute the new eased value using the easing function,
        and calculate the step delta.

        If clamp is enabled, the eased value is constrained between 0 and 1.

        Returns:
            float: The new eased value after advancing one step.

        """
        if self.current_step < self.total_steps:
            self.current_step += 1
            self.progress_ratio = self.current_step / self.total_steps
            self.eased_value = self.easing_function(self.progress_ratio)
            if self._clamp:
                self.eased_value = max(0.0, min(self.eased_value, 1.0))
            self.step_delta = self.eased_value - self._last_eased_value
            self._last_eased_value = self.eased_value
        return self.eased_value

    def reset(self) -> None:
        """Reset the easing tracker to the initial state."""
        self.current_step = 0
        self.progress_ratio = 0.0
        self.step_delta = 0.0
        self.eased_value = 0.0
        self._last_eased_value = 0.0

    def is_complete(self) -> bool:
        """Check if the easing tracker has completed all steps.

        Returns:
            bool: True if all steps have been completed, False otherwise.

        """
        return self.current_step >= self.total_steps

    def __iter__(self) -> typing.Iterator[float]:
        """Iterate over eased values until completion.

        Yields:
            float: The eased value at each step.

        """
        while not self.is_complete():
            yield self.step()


_T = typing.TypeVar("_T")


@dataclass
class SequenceEaser(typing.Generic[_T]):
    """Eases over a sequence, tracking added, removed, and total elements.

    Attributes:
        sequence (Sequence[_T]): The sequence to ease over.
        easing_function (EasingFunction): The easing function to use.
        total_steps (int): The total number of steps for the easing function.
        added (Sequence[_T]): Elements added in the current step.
        removed (Sequence[_T]): Elements removed in the current step.
        total (Sequence[_T]): Current active elements based on eased length.

    """

    sequence: typing.Sequence[_T]
    easing_function: EasingFunction
    total_steps: int = 100
    added: typing.Sequence[_T] = field(init=False, default_factory=list)
    removed: typing.Sequence[_T] = field(init=False, default_factory=list)
    total: typing.Sequence[_T] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        """Initialize the SequenceEaser."""
        self.easing_tracker = EasingTracker(
            easing_function=self.easing_function,
            total_steps=self.total_steps,
            clamp=True,
        )

    def step(self) -> typing.Sequence[_T]:
        """Advance the easing tracker by one step and update added, removed, and total elements.

        Returns:
            typing.Sequence[_T]: The elements added in the current step.

        """
        previous_eased = self.easing_tracker.eased_value
        eased_value = self.easing_tracker.step()
        seq_len = len(self.sequence)
        if seq_len == 0:
            self.added = self.sequence[:0]
            self.removed = self.sequence[:0]
            self.total = self.sequence[:0]
            return self.added

        length = int(eased_value * seq_len)
        previous_length = int(previous_eased * seq_len)

        if length > previous_length:
            self.added = self.sequence[previous_length:length]
            self.removed = self.sequence[:0]
        elif length < previous_length:
            self.added = self.sequence[:0]
            self.removed = self.sequence[length:previous_length]
        else:
            self.added = self.sequence[:0]
            self.removed = self.sequence[:0]

        self.total = self.sequence[:length]
        return self.added

    def is_complete(self) -> bool:
        """Check if the easing over the sequence is complete.

        Returns:
            bool: True if all steps have been completed, False otherwise.

        """
        return self.easing_tracker.is_complete()

    def reset(self) -> None:
        """Reset the SequenceEaser to the initial state."""
        self.easing_tracker.reset()
        self.added = self.sequence[:0]
        self.removed = self.sequence[:0]
        self.total = self.sequence[:0]
