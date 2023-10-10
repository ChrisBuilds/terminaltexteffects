import typing
import random
from dataclasses import dataclass, field

from terminaltexteffects.utils import ansitools, colorterm, hexterm

if typing.TYPE_CHECKING:
    from terminaltexteffects import base_character


@dataclass
class Gradient:
    """A Gradient is a list of RGB hex color strings transitioning from one color to another. The gradient color
    list is calculated using linear interpolation based on the provided start and end colors and the number of steps.

    Args:
        start_color (str|int): RGB hex color string or XTerm-256 color code
        end_color (str|int): RGB hex color string or XTerm-256 color code
        steps (int): Number of intermediate colors to calculate

    Attributes:
        colors (list[str]): List (length=steps + 2) of RGB hex color strings

    """

    start_color: str | int
    end_color: str | int
    steps: int

    def __post_init__(self):
        self.colors: list[str] = self._generate()
        self.index: int = 0

    def _generate(self) -> list[str]:
        """Calculate a gradient of colors between two colors using linear interpolation.

        Returns:
            list[str]: List (length=steps + 2) of RGB hex color strings
        """
        # Convert start_color to hex if it's an XTerm-256 color code
        if isinstance(self.start_color, int):
            self.start_color = hexterm.xterm_to_hex(self.start_color)
        # Convert end_color to hex if it's an XTerm-256 color code
        if isinstance(self.end_color, int):
            self.end_color = hexterm.xterm_to_hex(self.end_color)
        # Convert start_color to a list of RGB values
        start_color_ints = colorterm._hex_to_int(self.start_color)
        # Convert end_color to a list of RGB values
        end_color_ints = colorterm._hex_to_int(self.end_color)
        # Initialize an empty list to store the gradient colors
        gradient_colors = []
        # Add the start color to the gradient colors list
        gradient_colors.append(self.start_color)
        # Calculate the color deltas for each RGB value
        red_delta = (end_color_ints[0] - start_color_ints[0]) // self.steps
        green_delta = (end_color_ints[1] - start_color_ints[1]) // self.steps
        blue_delta = (end_color_ints[2] - start_color_ints[2]) // self.steps
        # Calculate the intermediate colors and add them to the gradient colors list
        for i in range(self.steps):
            red = start_color_ints[0] + (red_delta * i)
            green = start_color_ints[1] + (green_delta * i)
            blue = start_color_ints[2] + (blue_delta * i)

            # Ensure that the RGB values are within the valid range of 0-255
            red = max(0, min(red, 255))
            green = max(0, min(green, 255))
            blue = max(0, min(blue, 255))

            # Convert the RGB values to a hex color string and add it to the gradient colors list
            gradient_colors.append(f"{red:02x}{green:02x}{blue:02x}")
        # Add the end color to the gradient colors list
        gradient_colors.append(self.end_color)
        # Return the list of gradient colors
        return gradient_colors

    def __iter__(self):
        self.index = 0
        return self

    def __next__(self) -> str:
        if self.index < len(self.colors):
            color = self.colors[self.index]
            self.index += 1
            return color
        else:
            raise StopIteration

    def __add__(self, other: "Gradient"):
        if not isinstance(other, Gradient):
            return NotImplemented
        new_gradient = Gradient("ffffff", "ffffff", 1)
        new_gradient.colors = self.colors + other.colors
        new_gradient.steps = self.steps + other.steps
        new_gradient.start_color = self.start_color
        new_gradient.end_color = other.end_color
        return new_gradient


@dataclass
class GraphicalEffect:
    """A class for storing terminal graphical modes and a color.

    Supported graphical modes:
    bold, dim, italic, underline, blink, inverse, hidden, strike

    Args:
        symbol (str): the symbol to show
        bold (bool): bold mode
        dim (bool): dim mode
        italic (bool): italic mode
        underline (bool): underline mode
        blink (bool): blink mode
        reverse (bool): reverse mode
        hidden (bool): hidden mode
        strike (bool): strike mode
        color (int | str): color code
    """

    symbol: str
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False
    blink: bool = False
    reverse: bool = False
    hidden: bool = False
    strike: bool = False
    color: int | str | None = None

    def __post_init__(self):
        self.format_symbol()

    def disable_modes(self) -> None:
        """Disables all graphical modes."""
        self.bold = False
        self.dim = False
        self.italic = False
        self.underline = False
        self.blink = False
        self.reverse = False
        self.hidden = False
        self.strike = False

    def format_symbol(self) -> None:
        """Formats the symbol for printing."""
        formatting_string = ""
        if self.bold:
            formatting_string += ansitools.APPLY_BOLD()
        if self.italic:
            formatting_string += ansitools.APPLY_ITALIC()
        if self.underline:
            formatting_string += ansitools.APPLY_UNDERLINE()
        if self.blink:
            formatting_string += ansitools.APPLY_BLINK()
        if self.reverse:
            formatting_string += ansitools.APPLY_REVERSE()
        if self.hidden:
            formatting_string += ansitools.APPLY_HIDDEN()
        if self.strike:
            formatting_string += ansitools.APPLY_STRIKETHROUGH()
        if self.color is not None:
            formatting_string += colorterm.fg(self.color)

        self.symbol = f"{formatting_string}{self.symbol}{ansitools.RESET_ALL() if formatting_string else ''}"


@dataclass
class Sequence:
    """An Sequence is a graphicaleffect with a duration.
    Args:
        graphical_effect (GraphicalEffect): a GraphicalEffect object containing the graphical modes and color of the character
        duration (int): the number of animation steps to use the Sequence
    """

    graphical_effect: GraphicalEffect
    duration: int

    def __post_init__(self):
        self.frames_played = 0
        self.symbol = self.graphical_effect.symbol


@dataclass
class Scene:
    """A Scene is a list of Sequences.

    Args:
        id (str): the id of the Scene
        sequences (list[Sequence]): a list of Sequence objects
        is_looping (bool): whether the Scene should loop
    """

    id: str
    sequences: list[Sequence] = field(default_factory=list)
    is_looping: bool = False
    waypoint_sync_id: str | None = None

    def __post_init__(self):
        self.played_sequences = []

    def add_sequence(self, graphicaleffect: GraphicalEffect, duration: int) -> None:
        """Adds a Sequence to the Scene.

        Args:
            graphicaleffect (GraphicalEffect): a GraphicalEffect object containing the graphical modes and color of the character
            duration (int): the number of animation steps to use the Sequence
        """
        self.sequences.append(Sequence(graphicaleffect, duration))

    def activate(self) -> str:
        """Activates the Scene.

        Returns:
            str: the next symbol in the Scene
        """
        if self.sequences:
            return self.sequences[0].symbol
        else:
            raise ValueError("Scene has no sequences.")

    def apply_gradient(self, start_color: str | int, end_color: str | int) -> None:
        """
        Applies a gradient effect across the sequences of the scene. The gradient is generated
        to have the same number of steps as the number of sequences in the scene.

        Parameters
        ----------
        start_color : str | int
            The starting color of the gradient.
        end_color : str | int
            The ending color of the gradient.

        Returns
        -------
        None
        """
        if not self.sequences:
            return
        else:
            gradient = Gradient(start_color, end_color, len(self.sequences))
            for i, sequence in enumerate(self.sequences):
                sequence.graphical_effect.color = gradient.colors[i]
                sequence.graphical_effect.format_symbol()

    def get_next_symbol(self) -> str:
        """Returns the next symbol in the Scene.

        Returns:
            str: the next symbol in the Scene
        """

        current_sequence = self.sequences[0]
        next_symbol = current_sequence.symbol
        current_sequence.frames_played += 1
        if current_sequence.frames_played == current_sequence.duration:
            current_sequence.frames_played = 0
            self.played_sequences.append(self.sequences.pop(0))
            if self.is_looping and not self.sequences:
                self.sequences.extend(self.played_sequences)
                self.played_sequences.clear()
        return next_symbol

    def reset_scene(self) -> None:
        """Resets the Scene."""
        for sequence in self.sequences:
            sequence.frames_played = 0
            self.played_sequences.append(sequence)
        self.sequences.clear()
        self.sequences.extend(self.played_sequences)
        self.played_sequences.clear()

    def __eq__(self, other: "Scene") -> bool:
        if not isinstance(other, Scene):
            return NotImplemented
        return self.id == other.id


class Animation:
    def __init__(self, character: "base_character.EffectCharacter"):
        """Animation handles the animations of a character. It contains a list of Scenes, and the active scene id. GraphicalEffects are
        added to the Scenes, and the Animation returns the next symbol in the active scene.

        Args:
            character (base_character.EffectCharacter): the EffectCharacter object to animate
        """
        self.character = character
        self.scenes: dict[str, Scene] = {}
        self.active_scene: Scene | None = None
        self.use_xterm_colors: bool = False
        self.no_color: bool = False
        self.xterm_color_map: dict[str, int] = {}

    def add_effect_to_scene(
        self,
        scene_id: str,
        symbol: str | None | GraphicalEffect = None,
        color: int | str | None = None,
        duration: int = 1,
    ) -> None:
        """Add a graphical effect to a scene. If the scene doesn't exist, it will be created.

        Args:
            scene_id (str): ID of the scene to which the effect will be added
            symbol (str | GraphicalEffect): Symbol to display, if None, the character's input symbol will be used. If a GraphicalEffect is passed, the color and graphical modes will be used.
            color (int | str): XTerm color code (0-255) or hex color code (e.g. ffffff)
            duration (int): Number of animation steps to display the effect, defaults to 1. Minimum 1.
        """
        if duration < 1:
            raise ValueError("duration must be greater than 0")
        if scene_id not in self.scenes:
            new_scene = Scene(scene_id)
            self.scenes[scene_id] = new_scene
        if not symbol:
            symbol = self.character.input_symbol
        if not self.no_color:
            if self.use_xterm_colors and isinstance(color, str):
                if color in self.xterm_color_map:
                    color = self.xterm_color_map[color]
                else:
                    xterm_color = hexterm.hex_to_xterm(color)
                    self.xterm_color_map[color] = xterm_color
                    color = xterm_color
        else:
            color = None
        if isinstance(symbol, str):
            graphicaleffect = GraphicalEffect(symbol, color=color)
        else:
            graphicaleffect = symbol
        self.scenes[scene_id].add_sequence(graphicaleffect, duration)

    def active_scene_is_complete(self) -> bool:
        """Returns whether the active scene is complete. A scene is complete if all sequences have been played.
        Looping scenes are always complete.

        Returns:
            bool: True if complete, False otherwise
        """
        if not self.active_scene:
            return True
        elif not self.active_scene.sequences or self.active_scene.is_looping:
            return True
        elif self.active_scene.waypoint_sync_id is not None:
            if (
                self.character.motion.active_waypoint is None
                or self.character.motion.active_waypoint.id != self.active_scene.waypoint_sync_id
            ):
                return True
        return False

    def random_color(self) -> str:
        """Returns a random hex color code.

        Returns:
            str: hex color code
        """
        return hex(random.randint(0, 0xFFFFFF))[2:].zfill(6)

    def step_animation(self) -> None:
        """Apply the next symbol in the scene to the character. If a scene order exists, the next scene
        will be activated when the current scene is complete."""
        if self.active_scene and self.active_scene.sequences:
            # if the active scene is synced to the active waypoint, calculate the sequence index based on the
            # current waypoint progress
            if self.active_scene.waypoint_sync_id is not None:
                if (
                    self.character.motion.active_waypoint
                    and self.character.motion.active_waypoint.id == self.active_scene.waypoint_sync_id
                ):
                    sequence_index = round(
                        len(self.active_scene.sequences)
                        * (
                            max(self.character.motion.inter_waypoint_current_step, 1)
                            / max(self.character.motion.inter_waypoint_max_steps, 1)
                        )
                    )
                    try:
                        self.character.symbol = self.active_scene.sequences[sequence_index].symbol
                    except IndexError:
                        self.character.symbol = self.active_scene.sequences[-1].symbol
                else:  # when the active waypoint has been deactivated or changed, use the final symbol in the scene
                    self.character.symbol = self.active_scene.sequences[-1].symbol
            else:
                self.character.symbol = self.active_scene.get_next_symbol()
            if self.active_scene_is_complete():
                completed_scene_id = self.active_scene.id
                if not self.active_scene.is_looping:
                    self.active_scene.reset_scene()
                    self.active_scene = None

                self.character.event_handler.handle_event(
                    self.character.event_handler.Event.SCENE_COMPLETE, completed_scene_id
                )

    def reset_scene(self, scene_id: str) -> None:
        """Resets the Scene.

        Args:
            scene_name (str): the ID of the Scene to reset
        """
        if scene_id in self.scenes:
            self.scenes[scene_id].reset_scene()

    def activate_scene(self, scene_id: str) -> None:
        """Sets the active scene.

        Args:
            scene_id (str): the ID of the Scene to set as active
        """
        if scene_id in self.scenes:
            self.active_scene = self.scenes[scene_id]
            self.character.symbol = self.active_scene.activate()
            self.character.event_handler.handle_event(self.character.event_handler.Event.SCENE_ACTIVATED, scene_id)
        else:
            raise ValueError(f"Scene {scene_id} does not exist")

    def deactivate_scene(self, scene_id: str) -> None:
        """Deactivates a scene.

        Args:
            scene_id (str): the ID of the Scene to deactivate
        """
        if self.active_scene.id == scene_id:
            self.active_scene = None
