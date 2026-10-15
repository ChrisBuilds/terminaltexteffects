"""The text gradient: its settings, the toolbar chip that shows it, and the dialog that builds it."""

from __future__ import annotations

import dataclasses
import typing

from rich.segment import Segment
from rich.style import Style
from textual import events, on
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Select

from terminaltexteffects.tui.picker import ColorScreen
from terminaltexteffects.utils.graphics import Color, Gradient

if typing.TYPE_CHECKING:
    from textual.app import ComposeResult

Layer = typing.Literal["fg", "bg"]

DIRECTIONS: dict[str, Gradient.Direction] = {
    "horizontal": Gradient.Direction.HORIZONTAL,
    "vertical": Gradient.Direction.VERTICAL,
    "diagonal": Gradient.Direction.DIAGONAL,
    "radial": Gradient.Direction.RADIAL,
}
"""Gradient directions offered in the dialog, by the name shown."""

MAX_STEPS = 100
"""Most steps allowed between two stops."""


@dataclasses.dataclass(frozen=True)
class TextGradient:
    """A gradient to color text with.

    Attributes:
        stops (tuple[Color, ...]): Colors the gradient passes through, in order.
        steps (int): Colors between each pair of stops.
        direction (str): Key of `DIRECTIONS` the gradient runs in across the selection.
        layer (Layer): Whether the gradient colors the text (`fg`) or its background (`bg`).

    """

    stops: tuple[Color, ...] = (Color("8A008A"), Color("00D1FF"), Color("FFFFFF"))
    steps: int = 12
    direction: str = "horizontal"
    layer: Layer = "fg"

    def build(self) -> Gradient:
        """Return the `Gradient` for these settings."""
        return Gradient(*self.stops, steps=self.steps)


def gradient_strip(gradient: TextGradient, width: int, base: Style | None = None) -> Strip:
    """Return `width` cells colored across `gradient`, from its first stop to its last."""
    if width <= 0:
        return Strip.blank(0)
    built = gradient.build()
    segments = [
        Segment(
            " ", (base or Style()) + Style(bgcolor=f"#{built.get_color_at_fraction(x / max(1, width - 1)).rgb_color}")
        )
        for x in range(width)
    ]
    return Strip(segments, width)


class GradientBar(Widget):
    """A one-row preview of a `TextGradient` across the widget's width."""

    DEFAULT_CSS = """
    GradientBar {
        width: 1fr;
        height: 1;
    }
    """

    def __init__(self, gradient: TextGradient, **kwargs: typing.Any) -> None:
        """Initialize the preview of `gradient`."""
        super().__init__(**kwargs)
        self.gradient = gradient

    def show(self, gradient: TextGradient) -> None:
        """Preview `gradient`."""
        self.gradient = gradient
        self.refresh()

    def render_line(self, y: int) -> Strip:  # noqa: ARG002
        """Render the gradient across the widget's width."""
        return gradient_strip(self.gradient, self.size.width)


class GradientChip(Widget):
    """A toolbar chip drawn with the gradient's colors. Clicking it applies the gradient; its arrow edits it."""

    DEFAULT_CSS = """
    GradientChip {
        width: 21;
        height: 1;
    }
    """

    _ARROW = " ▾"
    _LABEL = "Gradient "

    class Apply(Message):
        """Posted when the chip is clicked, to apply the gradient to the selection."""

    class Edit(Message):
        """Posted when the chip's arrow is clicked, to open the gradient dialog."""

    def __init__(self, gradient: TextGradient, **kwargs: typing.Any) -> None:
        """Initialize the chip showing `gradient`."""
        super().__init__(**kwargs)
        self.gradient = gradient
        self._over_arrow = False
        self._update_tooltip()

    def show(self, gradient: TextGradient) -> None:
        """Show `gradient`."""
        self.gradient = gradient
        self._update_tooltip()
        self.refresh()

    def _update_tooltip(self) -> None:
        layer = "text" if self.gradient.layer == "fg" else "background"
        self.tooltip = (
            f"Color the selected {layer} with this {self.gradient.direction} gradient. Click ▾ to change the gradient."
        )

    def render_line(self, y: int) -> Strip:  # noqa: ARG002
        """Render the label, the gradient, and the arrow."""
        base = self.rich_style
        width = self.size.width
        swatch = max(1, width - len(self._LABEL) - len(self._ARROW))
        label = Strip([Segment(self._LABEL, base)])
        arrow_style = base + Style(bgcolor=self.app.theme_variables.get("primary", "#8A008A"), bold=True)
        arrow = Strip([Segment(self._ARROW, arrow_style if self._over_arrow else base)])
        return Strip.join([label, gradient_strip(self.gradient, swatch, base), arrow]).crop_extend(0, width, base)

    def _at_arrow(self, x: int) -> bool:
        return x >= self.size.width - len(self._ARROW)

    def on_mouse_move(self, event: events.MouseMove) -> None:
        """Highlight the arrow while the mouse is over it."""
        over = self._at_arrow(event.x)
        if over != self._over_arrow:
            self._over_arrow = over
            self.refresh()

    def on_leave(self) -> None:
        """Drop the arrow's highlight."""
        self._over_arrow = False
        self.refresh()

    def on_click(self, event: events.Click) -> None:
        """Edit the gradient when the arrow is clicked, and apply it otherwise."""
        if self._at_arrow(event.x):
            self.post_message(GradientChip.Edit())
        else:
            self.post_message(GradientChip.Apply())


class GradientScreen(ModalScreen["TextGradient | None"]):
    """Builds a text gradient: its stops, steps between them, direction, and whether it colors text or background.

    Returns the new gradient, or `None` when cancelled.
    """

    DEFAULT_CSS = """
    GradientScreen {
        align: center middle;
    }
    GradientScreen > Vertical {
        width: 60;
        max-width: 100%;
        height: auto;
        border: round $primary;
        border-title-color: $text;
        border-subtitle-color: $text-muted;
        background: $surface;
        padding: 1 2;
    }
    GradientScreen #preview {
        height: 2;
        margin-bottom: 1;
    }
    GradientScreen .row {
        height: auto;
        margin-bottom: 1;
    }
    GradientScreen .row > Label {
        width: 11;
        margin-top: 1;
        color: $text-muted;
    }
    GradientScreen #steps {
        width: 10;
    }
    GradientScreen #steps.-invalid {
        color: $text-error;
    }
    GradientScreen Select {
        width: 1fr;
    }
    GradientScreen #edit-stops {
        width: 1fr;
    }
    GradientScreen .buttons {
        height: auto;
        align-horizontal: right;
    }
    GradientScreen .buttons Button {
        margin-left: 1;
    }
    """

    BINDINGS: typing.ClassVar = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "apply", "Apply"),
    ]

    def __init__(self, gradient: TextGradient, *, has_selection: bool) -> None:
        """Initialize the dialog with `gradient`, saying whether applying it will color a selection."""
        super().__init__()
        self.gradient = gradient
        self._has_selection = has_selection

    def compose(self) -> ComposeResult:
        """Create the preview and the settings."""
        with Vertical() as dialog:
            dialog.border_title = "Gradient"
            dialog.border_subtitle = "Esc cancel · Ctrl+S apply"
            yield GradientBar(self.gradient, id="preview")
            with Horizontal(classes="row"):
                yield Label("Stops")
                yield Button(self._stops_label(), id="edit-stops", tooltip="Add, remove, reorder, and pick stop colors")
            with Horizontal(classes="row"):
                yield Label("Steps")
                yield Input(str(self.gradient.steps), id="steps", type="integer", tooltip=f"1 to {MAX_STEPS}")
            with Horizontal(classes="row"):
                yield Label("Direction")
                yield Select(
                    [(name.capitalize(), name) for name in DIRECTIONS],
                    value=self.gradient.direction,
                    allow_blank=False,
                    id="direction",
                )
            with Horizontal(classes="row"):
                yield Label("Colors")
                yield Select(
                    [("Text", "fg"), ("Background", "bg")],
                    value=self.gradient.layer,
                    allow_blank=False,
                    id="layer",
                )
            with Horizontal(classes="buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Apply to selection" if self._has_selection else "Save", variant="primary", id="apply")

    def on_mount(self) -> None:
        """Focus the steps field."""
        self.query_one("#steps", Input).focus()

    def _stops_label(self) -> str:
        return " ".join(stop.rgb_color for stop in self.gradient.stops) + "  ▸"

    def _update(self, **changes: typing.Any) -> None:
        self.gradient = dataclasses.replace(self.gradient, **changes)
        self.query_one(GradientBar).show(self.gradient)
        self.query_one("#edit-stops", Button).label = self._stops_label()

    @on(Button.Pressed, "#edit-stops")
    def _edit_stops(self) -> None:
        def picked(result: tuple[Color, ...] | None) -> None:
            if result:
                self._update(stops=tuple(result))

        self.app.push_screen(ColorScreen("gradient stops", self.gradient.stops, multiple=True), picked)

    @on(Input.Changed, "#steps")
    def _steps_changed(self, event: Input.Changed) -> None:
        try:
            steps = int(event.value)
        except ValueError:
            steps = 0
        valid = 1 <= steps <= MAX_STEPS
        event.input.set_class(not valid, "-invalid")
        if valid:
            self._update(steps=steps)

    @on(Select.Changed, "#direction")
    def _direction_changed(self, event: Select.Changed) -> None:
        if isinstance(event.value, str):
            self._update(direction=event.value)

    @on(Select.Changed, "#layer")
    def _layer_changed(self, event: Select.Changed) -> None:
        if event.value in ("fg", "bg"):
            self._update(layer=typing.cast("Layer", event.value))

    @on(Button.Pressed, "#apply")
    def action_apply(self) -> None:
        """Close the dialog and return the gradient."""
        self.dismiss(self.gradient)

    @on(Button.Pressed, "#cancel")
    def action_cancel(self) -> None:
        """Close the dialog without changing the gradient."""
        self.dismiss(None)
