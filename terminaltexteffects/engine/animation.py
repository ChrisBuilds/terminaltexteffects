from __future__ import annotations

import typing
from dataclasses import dataclass
from enum import Enum, auto

from terminaltexteffects.utils import ansitools, colorterm, easing, graphics, hexterm

if typing.TYPE_CHECKING:
    from terminaltexteffects.engine import base_character  # pragma: no cover


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
        symbol (str): the unformatted symbol
        bold (bool): bold mode
        dim (bool): dim mode
        italic (bool): italic mode
        underline (bool): underline mode
        blink (bool): blink mode
        reverse (bool): reverse mode
        hidden (bool): hidden mode
        strike (bool): strike mode
        fg_color (graphics.Color | None): the symbol's foreground color
        bg_color (graphics.Color | None): the symbol's background color

    Attributes:
        formatted_symbol (str): the current symbol with all ANSI sequences applied
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
    fg_color: graphics.Color | None = None  # the Color object provided during initialization
    bg_color: graphics.Color | None = None  # the Color object provided during initialization
    # the _*_color_code attributes are used to store the actual 8-bit int or 24-bit hex str after applying terminal config args
    # these are used by colorterm to produce the ansi sequences, the *_color Color objects are present to enable
    # programmatic access to the character's current visual color
    _fg_color_code: str | int | None = None
    _bg_color_code: str | int | None = None

    def __post_init__(self):
        self.formatted_symbol = self.format_symbol()

    def format_symbol(self) -> str:
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
        if self._fg_color_code is not None:
            formatting_string += colorterm.fg(self._fg_color_code)
        if self._bg_color_code is not None:
            formatting_string += colorterm.bg(self._bg_color_code)

        return f"{formatting_string}{self.symbol}{ansitools.RESET_ALL() if formatting_string else ''}"


@dataclass
class Frame:
    """A Frame is a CharacterVisual with a duration.

    Args:
        character_visual (CharacterVisual): a CharacterVisual object
        duration (int): the number of ticks to display the Frame

    Attributes:
        character_visual (CharacterVisual): the CharacterVisual object for the Frame
        duration (int): the number of ticks to display the Frame
        ticks_elapsed (int): the number of ticks that have elapsed displaying this frame
    """

    character_visual: CharacterVisual
    duration: int

    def __post_init__(self):
        self.ticks_elapsed = 0


class Scene:
    """A Scene is a collection of Frames that can be played in sequence. Scenes can be looped and synced to movement.

    Args:
        scene_id (str): the ID of the Scene
        is_looping (bool, optional): Whether the Scene should loop. Defaults to False.
        sync (SyncMetric | None, optional): The type of sync to use for the Scene. Defaults to None.
        ease (easing.EasingFunction | None, optional): The easing function to use for the Scene. Defaults to None.
        no_color (bool, optional): Whether to ignore colors. Defaults to False.
        use_xterm_colors (bool, optional): Whether to convert all colors to XTerm-256 colors. Defaults to False.

    Methods:
        add_frame: Adds a Frame to the Scene.
        activate: Activates the Scene.
        get_next_visual: Gets the next CharacterVisual in the Scene.
        apply_gradient_to_symbols: Applies a gradient effect to a sequence of symbols.
        reset_scene: Resets the Scene.

    Attributes:
        scene_id (str): the ID of the Scene
        is_looping (bool): Whether the Scene should loop
        sync (SyncMetric | None): The type of sync to use for the Scene
        ease (easing.EasingFunction | None): The easing function to use for the Scene
        no_color (bool): Whether to ignore colors
        use_xterm_colors (bool): Whether to convert all colors to XTerm-256 colors
        frames (list[Frame]): The list of Frames in the Scene
        played_frames (list[Frame]): The list of Frames that have been played
        frame_index_map (dict[int, Frame]): A mapping of frame index to Frame
        easing_total_steps (int): The total number of steps in the easing function
        easing_current_step (int): The current step in the easing function
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
        fg_color: graphics.Color | None = None,
        bg_color: graphics.Color | None = None,
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
        self.fg_color: graphics.Color | None = fg_color
        self.bg_color: graphics.Color | None = bg_color
        self.frames: list[Frame] = []
        self.played_frames: list[Frame] = []
        self.frame_index_map: dict[int, Frame] = {}
        self.easing_total_steps: int = 0
        self.easing_current_step: int = 0

    def _get_color_code(self, color: graphics.Color | None) -> str | int | None:
        """Get the color code for the given color. RGB colors are converted to XTerm-256 colors if use_xterm_colors
        is True. If no_color is True, returns None. Otherwise, returns the RGB color.

        Args:
            color (graphics.Color | None): the color to get the code for

        Returns:
            str | int | None: the color code
        """
        if color:
            if self.no_color:
                return None
            elif self.use_xterm_colors:
                if color.xterm_color is not None:
                    return color.xterm_color
                elif color.rgb_color in self.xterm_color_map:
                    return self.xterm_color_map[color.rgb_color]
                else:
                    xterm_color = hexterm.hex_to_xterm(color.rgb_color)
                    self.xterm_color_map[color.rgb_color] = xterm_color
                    return xterm_color
            else:
                return color.rgb_color
        return None

    def add_frame(
        self,
        symbol: str,
        duration: int,
        *,
        fg_color: graphics.Color | None = None,
        bg_color: graphics.Color | None = None,
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
            duration (int): the number of frames to use the Frame
            fg_color (graphics.Color, optional): the foreground color to show. Defaults to None.
            bg_color (graphics.Color, optional): the background color to show. Defaults to None.
            bold (bool, optional): bold mode. Defaults to False.
            dim (bool, optional): dim mode. Defaults to False.
            italic (bool, optional): italic mode. Defaults to False.
            underline (bool, optional): underline mode. Defaults to False.
            blink (bool, optional): blink mode. Defaults to False.
            reverse (bool, optional): reverse mode. Defaults to False.
            hidden (bool, optional): hidden mode. Defaults to False.
            strike (bool, optional): strike mode. Defaults to False.
        """
        # override fg and bg colors if they are set in the Scene due to existing color handling = always
        if self.fg_color:
            fg_color = self.fg_color
        if self.bg_color:
            bg_color = self.bg_color

        # get the color code for the fg and bg colors
        char_vis_fg_color = self._get_color_code(fg_color)
        char_vis_bg_color = self._get_color_code(bg_color)

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
            fg_color=fg_color,
            bg_color=bg_color,
            _fg_color_code=char_vis_fg_color,
            _bg_color_code=char_vis_bg_color,
        )
        frame = Frame(char_vis, duration)
        self.frames.append(frame)
        for _ in range(frame.duration):
            self.frame_index_map[self.easing_total_steps] = frame
            self.easing_total_steps += 1

    def activate(self) -> CharacterVisual:
        """Activates the Scene by returning the first frame CharacterVisual. Called by the Animation object when the Scene is activated.

        Raises:
            ValueError: if the Scene has no frames

        Returns:
            CharacterVisual: the next CharacterVisual in the Scene
        """
        if self.frames:
            return self.frames[0].character_visual
        else:
            raise ValueError("Scene has no frames.")

    def get_next_visual(self) -> CharacterVisual:
        """
        This method is used to get the next CharacterVisual in the Scene. It first retrieves the current frame from the frames list.
        It then increments the ticks_elapsed attribute of the Frame. If the ticks_elapsed equals the duration
        of the current frame, it resets ticks_elapsed to 0 and moves the current frame from the frames list to the
        played_frames list. If the Scene is set to loop and all frames have been played, it refills the frames list with the
        frames from played_frames and clears played_frames. Finally, it returns the CharacterVisual of the current frame.

        Returns:
            CharacterVisual: The visual of the current frame in the Scene.
        """

        current_frame = self.frames[0]
        next_visual = current_frame.character_visual
        current_frame.ticks_elapsed += 1
        if current_frame.ticks_elapsed == current_frame.duration:
            current_frame.ticks_elapsed = 0
            self.played_frames.append(self.frames.pop(0))
            if self.is_looping and not self.frames:
                self.frames.extend(self.played_frames)
                self.played_frames.clear()
        return next_visual

    def apply_gradient_to_symbols(
        self, gradient: graphics.Gradient, symbols: typing.Sequence[str], duration: int, fg=True, bg=False
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
            gradient (graphics.Gradient): The gradient to apply.
            symbols (list[str]): The list of symbols to apply the gradient to.
            duration (int): The duration to show each frame.
            fg (bool, optional): Whether to apply the gradient to the foreground color. Defaults to True.
            bg (bool, optional): Whether to apply the gradient to the background color. Defaults to False.

        Returns:
            None

        Raises:
            ValueError: If fg and bg are both False or if the gradient has no colors in the spectrum.
        """
        if not fg and not bg:
            raise ValueError("At least one of fg or bg must be True.")
        if not gradient.spectrum:
            raise ValueError("Gradient must have at least one color in the spectrum.")
        last_index = 0
        for symbol_index, symbol in enumerate(symbols):
            symbol_progress = (symbol_index + 1) / len(symbols)
            gradient_index = int(symbol_progress * len(gradient.spectrum))
            for color in gradient.spectrum[last_index : max(gradient_index, 1)]:
                self.add_frame(symbol, duration, fg_color=color if fg else None, bg_color=color if bg else None)
            last_index = gradient_index

    def reset_scene(self) -> None:
        """Resets the Scene."""
        for sequence in self.frames:
            sequence.ticks_elapsed = 0
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
        progress the Scene and apply the next visual to the character.

        Args:
            character (base_character.EffectCharacter): the EffectCharacter object to animate

        Attributes:
            scenes (dict[str, Scene]): a mapping of scene IDs to Scene objects
            character (base_character.EffectCharacter): the EffectCharacter object to animate
            active_scene (Scene | None): the active Scene
            use_xterm_colors (bool): whether to convert all colors to XTerm-256 colors
            no_color (bool): whether to ignore colors
            existing_color_handling (str): how to handle color ANSI sequences from the input data
            input_fg_color (graphics.Color | None): the input foreground Color
            input_bg_color (graphics.Color | None): the input background Color
            xterm_color_map (dict[str, int]): a mapping of RGB color codes to XTerm-256 color codes
            active_scene_current_step (int): the current step in the active Scene
            current_character_visual (CharacterVisual): the current visual of the character

        Methods:
            new_scene: Creates a new Scene and adds it to the Animation.
            query_scene: Returns a Scene from the Animation.
            active_scene_is_complete: Returns whether the active scene is complete.
            set_appearance: Applies a symbol and color to the character.
            adjust_color_brightness: Adjusts the brightness of a given color.
            _ease_animation: Returns the percentage of total distance that should be moved based on the easing function.
            step_animation: Apply the next symbol in the scene to the character.
            activate_scene: Activates a Scene.
        """
        self.scenes: dict[str, Scene] = {}
        self.character = character
        self.active_scene: Scene | None = None
        self.use_xterm_colors: bool = False
        self.no_color: bool = False
        self.existing_color_handling: typing.Literal["always", "dynamic", "ignore"] = "ignore"
        self.input_fg_color: graphics.Color | None = None
        self.input_bg_color: graphics.Color | None = None
        self.xterm_color_map: dict[str, int] = {}
        self.active_scene_current_step: int = 0
        self.current_character_visual: CharacterVisual = CharacterVisual(character.input_symbol)

    def _get_color_code(self, color: graphics.Color | None) -> str | int | None:
        """Get the color code for the given color. RGB colors are converted to XTerm-256 colors if use_xterm_colors
        is True. If no_color is True, returns None. Otherwise, returns the RGB color.

        Args:
            color (graphics.Color | None): the color to get the code for

        Returns:
            str | int | None: the color code
        """
        if color:
            if self.no_color:
                return None
            elif self.use_xterm_colors:
                if color.xterm_color is not None:
                    return color.xterm_color
                elif color.rgb_color in self.xterm_color_map:
                    return self.xterm_color_map[color.rgb_color]
                else:
                    xterm_color = hexterm.hex_to_xterm(color.rgb_color)
                    self.xterm_color_map[color.rgb_color] = xterm_color
                    return xterm_color
            else:
                return color.rgb_color
        return None

    def new_scene(
        self,
        *,
        is_looping: bool = False,
        sync: SyncMetric | None = None,
        ease: easing.EasingFunction | None = None,
        id: str = "",
    ) -> Scene:
        """Creates a new Scene and adds it to the Animation. If no ID is provided, a unique ID is generated.

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
                id = f"{current_id}"
                if id not in self.scenes:
                    found_unique = True
                else:
                    current_id += 1
        if self.existing_color_handling == "always":
            fg_color = self.input_fg_color
            bg_color = self.input_bg_color
        else:
            fg_color = None
            bg_color = None
        new_scene = Scene(
            scene_id=id,
            is_looping=is_looping,
            sync=sync,
            ease=ease,
            no_color=self.no_color,
            use_xterm_colors=self.use_xterm_colors,
            fg_color=fg_color,
            bg_color=bg_color,
        )
        self.scenes[id] = new_scene
        return new_scene

    def query_scene(self, scene_id: str) -> Scene:
        """Returns a Scene from the Animation. If the scene doesn't exist, raises a ValueError.

        Args:
            scene_id (str): the ID of the Scene

        Raises:
            ValueError: if the Scene does not exist

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

    def set_appearance(
        self, symbol: str, fg_color: graphics.Color | None = None, bg_color: graphics.Color | None = None
    ) -> None:
        """Updates the current character visual with the symbol and color provided. If the character has an active scene, any appearance set with this method
        will be overwritten when the scene is stepped to the next frame.

        Args:
            symbol (str): The symbol to apply.
            fg_color (graphics.Color | None): The foreground color to apply.
            bg_color (graphics.Color | None): The background color to apply.
        """
        # override fg and bg colors if they are set in the Scene due to existing color handling = always
        if self.existing_color_handling == "always":
            if self.input_fg_color:
                fg_color = self.input_fg_color
            if self.input_bg_color:
                bg_color = self.input_bg_color

        char_vis_fg_color: str | int | None = self._get_color_code(fg_color)
        char_vis_bg_color: str | int | None = self._get_color_code(bg_color)

        self.current_character_visual = CharacterVisual(
            symbol,
            fg_color=fg_color,
            _fg_color_code=char_vis_fg_color,
            bg_color=bg_color,
            _bg_color_code=char_vis_bg_color,
        )

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

        def hue_to_rgb(lightness_scaled: float, color_intensity: float, hue_value: float) -> float:
            """
            Converts a hue value to an RGB value component.

            This function is a helper function used in the conversion from HSL (Hue, Saturation, Lightness)
            color space to RGB (Red, Green, Blue) color space. It takes in three parameters: lightness_scaled,
            color_intensity, and hue_value. These parameters are derived from the HSL color space and are used
            to calculate the corresponding RGB value.

            Args:
                lightness_scaled (float): The lightness value from the HSL color space, scaled and shifted to be used in the RGB conversion.
                color_intensity (float): The intensity of the color, used to adjust the RGB values.
                hue_value (float): The hue value from the HSL color space, used to calculate the RGB values.

            Returns:
                float: The calculated RGB component.
            """

            if hue_value < 0:
                hue_value += 1
            if hue_value > 1:
                hue_value -= 1
            if hue_value < 1 / 6:
                return lightness_scaled + (color_intensity - lightness_scaled) * 6 * hue_value
            if hue_value < 1 / 2:
                return color_intensity
            if hue_value < 2 / 3:
                return lightness_scaled + (color_intensity - lightness_scaled) * (2 / 3 - hue_value) * 6
            return lightness_scaled

        normalized_red = int(color.rgb_color[0:2], 16) / 255
        normalized_green = int(color.rgb_color[2:4], 16) / 255
        normalized_blue = int(color.rgb_color[4:6], 16) / 255

        # Convert RGB to HSL
        max_val = max(normalized_red, normalized_green, normalized_blue)
        min_val = min(normalized_red, normalized_green, normalized_blue)
        lightness = (max_val + min_val) / 2

        if max_val == min_val:
            hue_value = saturation = 0.0  # achromatic
        else:
            diff = max_val - min_val
            saturation = diff / (2 - max_val - min_val) if lightness > 0.5 else diff / (max_val + min_val)
            if max_val == normalized_red:
                hue_value = (normalized_green - normalized_blue) / diff + (
                    6 if normalized_green < normalized_blue else 0
                )
            elif max_val == normalized_green:
                hue_value = (normalized_blue - normalized_red) / diff + 2
            else:
                hue_value = (normalized_red - normalized_green) / diff + 4
            hue_value /= 6

        # Adjust lightness
        lightness = max(min(lightness * brightness, 1), 0)

        # Convert back to RGB
        if saturation == 0:
            red = green = blue = lightness  # achromatic
        else:
            color_intensity = (
                lightness * (1 + saturation) if lightness < 0.5 else lightness + saturation - lightness * saturation
            )
            lightness_scaled = 2 * lightness - color_intensity
            red = hue_to_rgb(lightness_scaled, color_intensity, hue_value + 1 / 3)
            green = hue_to_rgb(lightness_scaled, color_intensity, hue_value)
            blue = hue_to_rgb(lightness_scaled, color_intensity, hue_value - 1 / 3)

        # Convert to hex
        adjusted_color = "{:02x}{:02x}{:02x}".format(int(red * 255), int(green * 255), int(blue * 255))
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
        """Progresses the Scene and applies the next visual to the character. If the active scene is complete, a SCENE_COMPLETE event is triggered."""
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
                        self.current_character_visual = self.active_scene.frames[sequence_index].character_visual
                    except IndexError:
                        self.current_character_visual = self.active_scene.frames[-1].character_visual
                else:  # when the active waypoint has been deactivated, use the final symbol in the scene and finish the scene
                    self.current_character_visual = self.active_scene.frames[-1].character_visual
                    self.active_scene.played_frames.extend(self.active_scene.frames)
                    self.active_scene.frames.clear()

            elif self.active_scene and self.active_scene.ease:
                easing_factor = self._ease_animation(self.active_scene.ease)
                frame_index = round(easing_factor * max(self.active_scene.easing_total_steps - 1, 0))
                frame_index = max(min(frame_index, self.active_scene.easing_total_steps - 1), 0)
                frame = self.active_scene.frame_index_map[frame_index]
                self.current_character_visual = frame.character_visual
                self.active_scene.easing_current_step += 1
                if self.active_scene.easing_current_step == self.active_scene.easing_total_steps:
                    if self.active_scene.is_looping:
                        self.active_scene.easing_current_step = 0
                    else:
                        self.active_scene.played_frames.extend(self.active_scene.frames)
                        self.active_scene.frames.clear()

            else:
                self.current_character_visual = self.active_scene.get_next_visual()
            if self.active_scene_is_complete():
                completed_scene = self.active_scene
                if not self.active_scene.is_looping:
                    self.active_scene.reset_scene()
                    self.active_scene = None

                self.character.event_handler._handle_event(
                    self.character.event_handler.Event.SCENE_COMPLETE, completed_scene
                )

    def activate_scene(self, scene: Scene) -> None:
        """Sets the active scene and updates the current character visual. A SCENE_ACTIVATED event is triggered.

        Args:
            scene (Scene): the Scene to set as active
        """
        self.active_scene = scene
        self.active_scene_current_step = 0
        self.current_character_visual = self.active_scene.activate()
        self.character.event_handler._handle_event(self.character.event_handler.Event.SCENE_ACTIVATED, scene)

    def deactivate_scene(self, scene: Scene) -> None:
        """Deactivates a scene.

        Args:
            scene (Scene): the Scene to deactivate
        """
        if self.active_scene is scene:
            self.active_scene = None
