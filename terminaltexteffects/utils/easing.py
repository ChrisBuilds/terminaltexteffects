import math


class Easing:
    @staticmethod
    def in_sine(step_ratio: float) -> float:
        """
        Ease in using a sine function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """
        return 1 - math.cos((step_ratio * math.pi) / 2)

    @staticmethod
    def out_sine(step_ratio: float) -> float:
        """
        Ease out using a sine function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """
        return math.sin((step_ratio * math.pi) / 2)

    @staticmethod
    def in_out_sine(step_ratio: float) -> float:
        """
        Ease in/out using a sine function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """

        return -(math.cos(math.pi * step_ratio) - 1) / 2

    @staticmethod
    def in_quad(step_ratio: float) -> float:
        """
        Ease in using a quadratic function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """

        return step_ratio**2

    @staticmethod
    def out_quad(step_ratio: float) -> float:
        """
        Ease out using a quadratic function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character

        """
        return 1 - (1 - step_ratio) * (1 - step_ratio)

    @staticmethod
    def in_out_quad(step_ratio: float) -> float:
        """
        Ease in/out using a quadratic function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character

        """
        if step_ratio < 0.5:
            return 2 * step_ratio**2
        else:
            return 1 - (-2 * step_ratio + 2) ** 2 / 2

    @staticmethod
    def in_cubic(step_ratio: float) -> float:
        """
        Ease in using a cubic function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """
        return step_ratio**3

    @staticmethod
    def out_cubic(step_ratio: float) -> float:
        """
        Ease out using a cubic function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """
        return 1 - (1 - step_ratio) ** 3

    @staticmethod
    def in_out_cubic(step_ratio: float) -> float:
        """
        Ease in/out using a cubic function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the
            character
        """
        if step_ratio < 0.5:
            return 4 * step_ratio**3
        else:
            return 1 - (-2 * step_ratio + 2) ** 3 / 2

    @staticmethod
    def in_quart(step_ratio: float) -> float:
        """
        Ease in using a quartic function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage
            of the current waypoint speed to apply to the character
        """
        return step_ratio**4

    @staticmethod
    def out_quart(step_ratio: float) -> float:
        """
        Ease out using a quartic function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """
        return 1 - (1 - step_ratio) ** 4

    @staticmethod
    def in_out_quart(step_ratio: float) -> float:
        """
        Ease in/out using a quartic function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """
        if step_ratio < 0.5:
            return 8 * step_ratio**4
        else:
            return 1 - (-2 * step_ratio + 2) ** 4 / 2

    @staticmethod
    def in_quint(step_ratio: float) -> float:
        """
        Ease in using a quintic function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """
        return step_ratio**5

    @staticmethod
    def out_quint(step_ratio: float) -> float:
        """
        Ease out using a quintic function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """
        return 1 - (1 - step_ratio) ** 5

    @staticmethod
    def in_out_quint(step_ratio: float) -> float:
        """
        Ease in/out using a quintic function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """
        if step_ratio < 0.5:
            return 16 * step_ratio**5
        else:
            return 1 - (-2 * step_ratio + 2) ** 5 / 2

    @staticmethod
    def in_expo(step_ratio: float) -> float:
        """
        Ease in using an exponential function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """
        if step_ratio == 0:
            return 0
        else:
            return 2 ** (10 * step_ratio - 10)

    @staticmethod
    def out_expo(step_ratio: float) -> float:
        """
        Ease out using an exponential function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """
        if step_ratio == 1:
            return 1
        else:
            return 1 - 2 ** (-10 * step_ratio)

    @staticmethod
    def in_out_expo(step_ratio: float) -> float:
        """
        Ease in/out using an exponential function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """
        if step_ratio == 0:
            return 0
        elif step_ratio == 1:
            return 1
        elif step_ratio < 0.5:
            return 2 ** (20 * step_ratio - 10) / 2
        else:
            return (2 - 2 ** (-20 * step_ratio + 10)) / 2

    @staticmethod
    def in_circ(step_ratio: float) -> float:
        """
        Ease in using a circular function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """
        return 1 - math.sqrt(1 - step_ratio**2)

    @staticmethod
    def out_circ(step_ratio: float) -> float:
        """
        Ease out using a circular function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """
        return math.sqrt(1 - (step_ratio - 1) ** 2)

    @staticmethod
    def in_out_circ(step_ratio: float) -> float:
        """
        Ease in/out using a circular function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """
        if step_ratio < 0.5:
            return (1 - math.sqrt(1 - (2 * step_ratio) ** 2)) / 2
        else:
            return (math.sqrt(1 - (-2 * step_ratio + 2) ** 2) + 1) / 2

    @staticmethod
    def in_back(step_ratio: float) -> float:
        """
        Ease in using a back function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """
        c1 = 1.70158
        c3 = c1 + 1
        return c3 * step_ratio**3 - c1 * step_ratio**2

    @staticmethod
    def out_back(step_ratio: float) -> float:
        """
        Ease out using a back function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """
        c1 = 1.70158
        c3 = c1 + 1
        return 1 + c3 * (step_ratio - 1) ** 3 + c1 * (step_ratio - 1) ** 2

    @staticmethod
    def in_out_back(step_ratio: float) -> float:
        """
        Ease in/out using a back function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """
        c1 = 1.70158
        c2 = c1 * 1.525
        if step_ratio < 0.5:
            return ((2 * step_ratio) ** 2 * ((c2 + 1) * 2 * step_ratio - c2)) / 2
        else:
            return ((2 * step_ratio - 2) ** 2 * ((c2 + 1) * (step_ratio * 2 - 2) + c2) + 2) / 2

    @staticmethod
    def in_elastic(step_ratio: float) -> float:
        """
        Ease in using an elastic function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage of the current waypoint speed to apply to the character
        """

        c4 = (2 * math.pi) / 3
        if step_ratio == 0:
            return 0
        elif step_ratio == 1:
            return 1
        else:
            return -(2 ** (10 * step_ratio - 10)) * math.sin((step_ratio * 10 - 10.75) * c4)

    @staticmethod
    def out_elastic(step_ratio: float) -> float:
        """
        Ease out using an elastic function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the percentage
            of the current waypoint speed to apply to the character
        """
        c4 = (2 * math.pi) / 3
        if step_ratio == 0:
            return 0
        elif step_ratio == 1:
            return 1
        else:
            return 2 ** (-10 * step_ratio) * math.sin((step_ratio * 10 - 0.75) * c4) + 1

    @staticmethod
    def in_out_elastic(step_ratio: float) -> float:
        """
        Ease in/out using an elastic function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the
            percentage of the current waypoint speed to apply to the character
        """
        c5 = (2 * math.pi) / 4.5
        if step_ratio == 0:
            return 0
        elif step_ratio == 1:
            return 1
        elif step_ratio < 0.5:
            return -(2 ** (20 * step_ratio - 10) * math.sin((20 * step_ratio - 11.125) * c5)) / 2
        else:
            return (2 ** (-20 * step_ratio + 10) * math.sin((20 * step_ratio - 11.125) * c5)) / 2 + 1

    @staticmethod
    def in_bounce(step_ratio: float) -> float:
        """
        Ease in using a bounce function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1 representing the
            percentage of the current waypoint speed to apply to the character
        """
        return 1 - Easing.out_bounce(1 - step_ratio)

    @staticmethod
    def out_bounce(step_ratio: float) -> float:
        """
        Ease out using a bounce function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <= 1
            representing the percentage of the current waypoint speed to apply to the character
        """
        n1 = 7.5625
        d1 = 2.75
        if step_ratio < 1 / d1:
            return n1 * step_ratio**2
        elif step_ratio < 2 / d1:
            return n1 * (step_ratio - 1.5 / d1) ** 2 + 0.75
        elif step_ratio < 2.5 / d1:
            return n1 * (step_ratio - 2.25 / d1) ** 2 + 0.9375
        else:
            return n1 * (step_ratio - 2.625 / d1) ** 2 + 0.984375

    @staticmethod
    def in_out_bounce(step_ratio: float) -> float:
        """
        Ease in/out using a bounce function.

        Args:
            step_ratio (float): the ratio of the current step to the maximum steps

        Returns:
            float: 0 <= n <=
            1 representing the percentage of the current waypoint speed to apply to the character
        """
        if step_ratio < 0.5:
            return (1 - Easing.out_bounce(1 - 2 * step_ratio)) / 2
        else:
            return (1 + Easing.out_bounce(2 * step_ratio - 1)) / 2
