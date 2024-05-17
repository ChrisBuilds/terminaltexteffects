import random
import typing
from dataclasses import dataclass
from enum import Enum, auto

from terminaltexteffects.utils import ansitools, colorterm, easing, graphics

if typing.TYPE_CHECKING:
    from terminaltexteffects.engine import base_character


class SyncMetric(Enum):
    """Enum for specifying the type of sync to use for a Scene.

    Attributes:
        DISTANCE (int): Sync to a Waypoint based on distance from the Waypoint
        STEP (int): Sync to a Waypoint based on the number of steps taken towards the Waypoint
    """

    DISTANCE = auto()
    STEP = auto()


@dataclass
class CharacterVisual:
    """A class for storing symbol, color, and terminal graphical modes for the character.

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
        color (Color): color code
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
    color: str | int | None = None

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
        """Formats the symbol for printing by applying ANSI sequences for any active modes and color."""
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
class Frame:
    """A Frame is a CharacterVisual with a duration.

    Args:
        character_visual (CharacterVisual): a CharacterVisual object
        duration (int): the number of frames to use the Frame
    """

    character_visual: CharacterVisual
    duration: int

    def __post_init__(self):
        self.frames_played = 0
        self.symbol = self.character_visual.symbol


class Scene:
    """A Scene is a collection of Frames that can be played in sequence. Scenes can be looped and synced to movement.

    Methods:
        add_frame: Adds a Frame to the Scene.
        activate: Activates the Scene.
        get_next_symbol: Returns the next symbol in the Scene.
        apply_gradient_to_symbols: Applies a gradient effect to a sequence of symbols.
        reset_scene: Resets the Scene.
    """

    xterm_color_map: dict[str, int] = {}

    def __init__(
        self,
        scene_id: str,
        is_looping: bool = False,
        sync: SyncMetric | None = None,
        ease: easing.EasingFunction | None = None,
        no_color: bool = False,
        use_xterm_colors: bool = False,
    ):
        """Initializes a Scene.

        Args:
            scene_id (str): the ID of the Scene
            is_looping (bool, optional): Whether the Scene should loop. Defaults to False.
            sync (SyncMetric | None, optional): The type of sync to use for the Scene. Defaults to None.
            ease (easing.EasingFunction | None, optional): The easing function to use for the Scene. Defaults to None.
            no_color (bool, optional): Whether to colors should be ignored. Defaults to False.
            use_xterm_colors (bool, optional): Whether to convert all colors to XTerm-256 colors. Defaults to False.
        """
        self.scene_id = scene_id
        self.is_looping = is_looping
        self.sync: SyncMetric | None = sync
        self.ease: easing.EasingFunction | None = ease
        self.no_color = no_color
        self.use_xterm_colors = use_xterm_colors
        self.frames: list[Frame] = []
        self.played_frames: list[Frame] = []
        self.frame_index_map: dict[int, Frame] = {}
        self.easing_total_steps: int = 0
        self.easing_current_step: int = 0

    def add_frame(
        self,
        symbol: str,
        duration: int,
        *,
        color: graphics.Color | None = None,
        bold=False,
        dim=False,
        italic=False,
        underline=False,
        blink=False,
        reverse=False,
        hidden=False,
        strike=False,
    ) -> None:
        """Adds a Frame to the Scene with the given symbol, duration, color, and graphical modes.

        Args:
            symbol (str): the symbol to show
            color (graphics.Color | None): Color
            duration (int): the number of frames to use the Frame
            color (str | int | None, optional): the color to show. Defaults to None.
            bold (bool, optional): bold mode. Defaults to False.
            dim (bool, optional): dim mode. Defaults to False.
            italic (bool, optional): italic mode. Defaults to False.
            underline (bool, optional): underline mode. Defaults to False.
            blink (bool, optional): blink mode. Defaults to False.
            reverse (bool, optional): reverse mode. Defaults to False.
            hidden (bool, optional): hidden mode. Defaults to False.
            strike (bool, optional): strike mode. Defaults to False.
        """
        char_vis_color: str | int | None = None
        if color:
            if self.no_color:
                char_vis_color = None
            elif self.use_xterm_colors:
                char_vis_color = color.xterm_color
            else:
                char_vis_color = color.rgb_color
        if duration < 1:
            raise ValueError("duration must be greater than 0")
        char_vis = CharacterVisual(
            symbol,
            bold=bold,
            dim=dim,
            italic=italic,
            underline=underline,
            blink=blink,
            reverse=reverse,
            hidden=hidden,
            strike=strike,
            color=char_vis_color,
        )
        frame = Frame(char_vis, duration)
        self.frames.append(frame)
        for _ in range(frame.duration):
            self.frame_index_map[self.easing_total_steps] = frame
            self.easing_total_steps += 1

    def activate(self) -> str:
        """Activates the Scene by returning the first frame symbol. Called by the Animation object when the Scene is activated.

        Raises:
            ValueError: if the Scene has no sequences

        Returns:
            str: the next symbol in the Scene
        """
        if self.frames:
            return self.frames[0].symbol
        else:
            raise ValueError("Scene has no sequences.")

    def get_next_symbol(self) -> str:
        """
        This method is used to get the next symbol in the Scene. It first retrieves the current sequence from the frames list.
        It then increments the 'frames_played' attribute of the current sequence. If the 'frames_played' equals the 'duration'
        of the current sequence, it resets 'frames_played' to 0 and moves the current sequence from the frames list to the
        'played_frames' list. If the Scene is set to loop and all frames have been played, it refills the frames list with the
        sequences from 'played_frames' and clears 'played_frames'. Finally, it returns the symbol of the current sequence.

        Returns:
            str: The symbol of the current sequence in the Scene.
        """

        current_sequence = self.frames[0]
        next_symbol = current_sequence.symbol
        current_sequence.frames_played += 1
        if current_sequence.frames_played == current_sequence.duration:
            current_sequence.frames_played = 0
            self.played_frames.append(self.frames.pop(0))
            if self.is_looping and not self.frames:
                self.frames.extend(self.played_frames)
                self.played_frames.clear()
        return next_symbol

    def apply_gradient_to_symbols(
        self, gradient: graphics.Gradient, symbols: typing.Sequence[str], duration: int
    ) -> None:
        """
        Applies a gradient effect to a sequence of symbols and adds each symbol as a frame to the Scene.

        This method works by iterating over the symbols and calculating a progress ratio for each symbol.
        This ratio is calculated by dividing the index of the current symbol (plus one) by the total number of symbols.
        The gradient index is then calculated by multiplying the symbol progress by the length of the gradient's spectrum.
        This index is used to select a color from the gradient's spectrum.

        The method then iterates over the colors in the gradient's spectrum from the last index to the gradient index
        (or 1 if gradient index is 0). For each color, it calls the add_frame method, passing the symbol, duration, and color.
        This adds a frame to the Scene with the symbol displayed in the color from the gradient.

        Finally, the last index is updated to the current gradient index, and the process repeats for the next symbol.
        This results in each symbol being displayed in a sequence of colors from the gradient, creating a gradient effect across the symbols.

        Args:
            gradient (Gradient): The gradient to apply.
            symbols (list[str]): The list of symbols to apply the gradient to.
            duration (int): The duration to show each frame.

        Returns:
            None
        """
        last_index = 0
        for symbol_index, symbol in enumerate(symbols):
            symbol_progress = (symbol_index + 1) / len(symbols)
            gradient_index = int(symbol_progress * len(gradient.spectrum))
            for color in gradient.spectrum[last_index : max(gradient_index, 1)]:
                self.add_frame(symbol, duration, color=color)
            last_index = gradient_index

    def reset_scene(self) -> None:
        """Resets the Scene."""
        for sequence in self.frames:
            sequence.frames_played = 0
            self.played_frames.append(sequence)
        self.frames.clear()
        self.frames.extend(self.played_frames)
        self.played_frames.clear()

    def __eq__(self, other: typing.Any):
        if not isinstance(other, Scene):
            return NotImplemented
        return self.scene_id == other.scene_id

    def __hash__(self):
        return hash(self.scene_id)


class Animation:
    def __init__(self, character: "base_character.EffectCharacter"):
        """Animation handles the animations of a character. It contains a scene_name -> Scene mapping and the active Scene. Calls to step_animation()
        progress the Scene and apply the next symbol to the character.

        Args:
            character (base_character.EffectCharacter): the EffectCharacter object to animate
        """
        self.scenes: dict[str, Scene] = {}
        self.character = character
        self.active_scene: Scene | None = None
        self.use_xterm_colors: bool = False
        self.no_color: bool = False
        self.xterm_color_map: dict[str, int] = {}
        self.active_scene_current_step: int = 0

    def new_scene(
        self,
        *,
        is_looping: bool = False,
        sync: SyncMetric | None = None,
        ease: easing.EasingFunction | None = None,
        id: str = "",
    ) -> Scene:
        """Creates a new Scene and adds it to the Animation.

        Args:
            id (str): Unique name for the scene. Used to query for the scene.
            is_looping (bool): Whether the scene should loop.
            sync (SyncMetric): The type of sync to use for the scene.
            ease (easing.EasingFunction): The easing function to use for the scene.

        Returns:
            Scene: the new Scene
        """
        if not id:
            found_unique = False
            current_id = len(self.scenes)
            while not found_unique:
                id = f"{len(self.scenes)}"
                if id not in self.scenes:
                    found_unique = True
                else:
                    current_id += 1

        new_scene = Scene(scene_id=id, is_looping=is_looping, sync=sync, ease=ease)
        self.scenes[id] = new_scene
        new_scene.no_color = self.no_color
        new_scene.use_xterm_colors = self.use_xterm_colors
        return new_scene

    def query_scene(self, scene_id: str) -> Scene:
        """Returns a Scene from the Animation. If the scene doesn't exist, raises a ValueError.

        Args:
            scene_id (str): the ID of the Scene

        Returns:
            Scene: the Scene
        """
        scene = self.scenes.get(scene_id, None)
        if not scene:
            raise ValueError(f"Scene {scene_id} does not exist.")
        return scene

    def active_scene_is_complete(self) -> bool:
        """Returns whether the active scene is complete. A scene is complete if all sequences have been played.
        Looping scenes are always complete.

        Returns:
            bool: True if complete, False otherwise
        """
        if not self.active_scene:
            return True
        elif not self.active_scene.frames or self.active_scene.is_looping:
            return True

        return False

    def set_appearance(self, symbol: str, color: graphics.Color | None = None) -> None:
        """Applies a symbol and color to the character. If the character has an active scene, any appearance set with this method
        will be overwritten when the scene is stepped to the next frame.

        Args:
            symbol (str): The symbol to apply.
            color (graphics.Color | None): The color to apply.
        """
        char_vis_color: str | int | None = None
        if color:
            if self.no_color:
                char_vis_color = None
            elif self.use_xterm_colors:
                char_vis_color = color.xterm_color
            else:
                char_vis_color = color.rgb_color
        visual = CharacterVisual(symbol, color=char_vis_color)
        self.character.symbol = visual.symbol

    @staticmethod
    def random_color() -> graphics.Color:
        """Returns a random color.

        Returns:
            graphics.Color: A random color.
        """
        return graphics.Color(hex(random.randint(0, 0xFFFFFF))[2:].zfill(6))

    @staticmethod
    def adjust_color_brightness(color: graphics.Color, brightness: float) -> graphics.Color:
        """
        Adjusts the brightness of a given color.

        Args:
            color (Color): The color code to adjust.
            brightness (float): The brightness adjustment factor.

        Returns:
            Color: The adjusted color code.
        """

        def hue_to_rgb(p: float, q: float, t: float) -> float:
            """
            Converts a hue value to an RGB value component.

            This function takes three parameters: p, q, and t. It calculates the RGB value component based on the given hue value.



            """

            if t < 0:
                t += 1
            if t > 1:
                t -= 1
            if t < 1 / 6:
                return p + (q - p) * 6 * t
            if t < 1 / 2:
                return q
            if t < 2 / 3:
                return p + (q - p) * (2 / 3 - t) * 6
            return p

        r: int | float
        g: int | float
        b: int | float
        r, g, b = color.rgb_ints

        # Convert RGB to HSL
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        lightness = (max_val + min_val) / 2

        if max_val == min_val:
            h = s = 0.0  # achromatic
        else:
            diff = max_val - min_val
            s = diff / (2 - max_val - min_val) if lightness > 0.5 else diff / (max_val + min_val)
            if max_val == r:
                h = (g - b) / diff + (6 if g < b else 0)
            elif max_val == g:
                h = (b - r) / diff + 2
            else:
                h = (r - g) / diff + 4
            h /= 6

        # Adjust lightness
        lightness = max(min(lightness * brightness, 1), 0)

        # Convert back to RGB
        if s == 0:
            r = g = b = lightness  # achromatic
        else:
            q = lightness * (1 + s) if lightness < 0.5 else lightness + s - lightness * s
            p = 2 * lightness - q
            r = hue_to_rgb(p, q, h + 1 / 3)
            g = hue_to_rgb(p, q, h)
            b = hue_to_rgb(p, q, h - 1 / 3)

        # Convert to hex
        adjusted_color = "{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))
        return graphics.Color(adjusted_color)

    def _ease_animation(self, easing_func: easing.EasingFunction) -> float:
        """Returns the percentage of total distance that should be moved based on the easing function.

        Args:
            easing_func (easing.EasingFunction): The easing function to use.

        Returns:
            float: The percentage of total distance to move.
        """

        if self.active_scene is None:
            return 0
        elapsed_step_ratio = self.active_scene.easing_current_step / self.active_scene.easing_total_steps
        return easing_func(elapsed_step_ratio)

    def step_animation(self) -> None:
        """Apply the next symbol in the scene to the character. If a scene order exists, the next scene
        will be activated when the current scene is complete."""
        if self.active_scene and self.active_scene.frames:
            # if the active scene is synced to movement, calculate the sequence index based on the
            # current waypoint progress
            if self.active_scene.sync:
                if self.character.motion.active_path:
                    if self.active_scene.sync == SyncMetric.STEP:
                        sequence_index = round(
                            (len(self.active_scene.frames) - 1)
                            * (
                                max(self.character.motion.active_path.current_step, 1)
                                / max(self.character.motion.active_path.max_steps, 1)
                            )
                        )
                    elif self.active_scene.sync == SyncMetric.DISTANCE:
                        sequence_index = round(
                            (len(self.active_scene.frames) - 1)
                            * (
                                max(
                                    max(self.character.motion.active_path.total_distance, 1)
                                    - max(
                                        self.character.motion.active_path.total_distance
                                        - self.character.motion.active_path.last_distance_reached,
                                        1,
                                    ),
                                    1,
                                )
                                / max(self.character.motion.active_path.total_distance, 1)
                            )
                        )
                    try:
                        self.character.symbol = self.active_scene.frames[sequence_index].symbol
                    except IndexError:
                        self.character.symbol = self.active_scene.frames[-1].symbol
                else:  # when the active waypoint has been deactivated, use the final symbol in the scene and finish the scene
                    self.character.symbol = self.active_scene.frames[-1].symbol
                    self.active_scene.played_frames.extend(self.active_scene.frames)
                    self.active_scene.frames.clear()

            elif self.active_scene and self.active_scene.ease:
                easing_factor = self._ease_animation(self.active_scene.ease)
                frame_index = round(easing_factor * max(self.active_scene.easing_total_steps - 1, 0))
                frame_index = max(min(frame_index, self.active_scene.easing_total_steps - 1), 0)
                frame = self.active_scene.frame_index_map[frame_index]
                self.character.symbol = frame.symbol
                self.active_scene.easing_current_step += 1
                if self.active_scene.easing_current_step == self.active_scene.easing_total_steps:
                    if self.active_scene.is_looping:
                        self.active_scene.easing_current_step = 0
                    else:
                        self.active_scene.played_frames.extend(self.active_scene.frames)
                        self.active_scene.frames.clear()

            else:
                self.character.symbol = self.active_scene.get_next_symbol()
            if self.active_scene_is_complete():
                completed_scene = self.active_scene
                if not self.active_scene.is_looping:
                    self.active_scene.reset_scene()
                    self.active_scene = None

                self.character.event_handler._handle_event(
                    self.character.event_handler.Event.SCENE_COMPLETE, completed_scene
                )

    def activate_scene(self, scene: Scene) -> None:
        """Sets the active scene.

        Args:
            scene (Scene): the Scene to set as active
        """
        self.active_scene = scene
        self.active_scene_current_step = 0
        self.character.symbol = self.active_scene.activate()
        self.character.event_handler._handle_event(self.character.event_handler.Event.SCENE_ACTIVATED, scene)

    def deactivate_scene(self, scene: Scene) -> None:
        """Deactivates a scene.

        Args:
            scene (Scene): the Scene to deactivate
        """
        if self.active_scene is scene:
            self.active_scene = None
