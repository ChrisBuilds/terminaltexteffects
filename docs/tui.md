# Interactive Interface

The interactive interface lets you type and arrange text, pick an effect, adjust its options, and preview the effect
on your text, all in one terminal window. It is an optional extra built on [Textual](https://textual.textualize.io/),
so the core package keeps no third-party dependencies.

![The interactive interface playing an effect](img/tui_demo.webp)

## Install

=== "pipx"

    ```bash
    pipx install 'terminaltexteffects[tui]'
    ```

=== "uv"

    ```bash
    uv tool install 'terminaltexteffects[tui]'
    ```

=== "pip"

    ```bash
    pip install 'terminaltexteffects[tui]'
    ```

## Start

| Command | What opens |
| --- | --- |
| `tte` | The interface with an empty text area. Without the extra installed, `tte` prints usage and the install command. |
| `ls -la \| tte` or `tte -i notes.txt` | The interface with that text loaded, when no effect is named. |
| `tte --tui` | The interface, with any piped or `-i` text loaded. Add an effect name to select it, such as `tte --tui decrypt`. |
| `tte decrypt < notes.txt` | The effect plays as usual. Naming an effect never opens the interface. |

The interface needs a terminal for output. When standard output is redirected, `tte` keeps its usual behavior and
`tte --tui` exits with an error.

## Layout

- **Effects** on the left lists every available effect, including [community effects](appguide.md#community-effects).
  Highlighting one shows its options. Pressing Enter on it plays it.
- **Text** fills the rest of the top of the screen. Type, paste, and arrange text here. The subtitle shows the canvas
  size.
- **Options** at the bottom has two tabs. **Effect** holds the selected effect's options, and **Canvas** holds the
  terminal options that affect previews: canvas size and anchors, text wrapping, frame rate, color handling, and tab
  width.

Option inputs follow each option's type: a checkbox for on/off options, a list for fixed choices such as gradient
directions and easing functions, and a text box for everything else. Text boxes use the same spelling as the
command line. Lists are space separated, such as `ff0000 00ff00 0000ff`, and colors show a swatch. An invalid value
turns its name and field red, with the reason in its tooltip, and the effect won't play until it is fixed. Changed
options have their names highlighted, and each effect keeps its own values while the interface is open. The
selected effect's description is shown along the bottom of the options panel.

### Picking colors

Color options open a color picker when you press ++f7++ or ++enter++ in the field, or click the swatch. Choose from
the 256 XTerm colors in the palette, type a hex value, or drag the hue, saturation, and lightness bars. Palette
colors stay XTerm colors on the command line, and any other change gives an RGB hex color. For gradient options,
the picker edits the list of stops: select a stop, change its color, and add, remove, or reorder stops while a bar
previews the gradient. Press ++ctrl+s++ or choose **Apply** to keep the colors, or ++escape++ to discard them.

## Keys

| Key | Action |
| --- | --- |
| ++f5++ | Play the selected effect over the text. |
| ++escape++ | Stop the effect, or clear the finished effect, and return to the text. |
| ++f2++ | Open a text file. |
| ++f3++ | Save the text to a file. |
| ++f4++ | Show the `tte` command that plays the effect with the current options, with a button to copy it. |
| ++f7++ | Open the color picker for the selected color option. |
| ++f6++ | Reset the selected effect's options and the canvas options. |
| ++f8++ | Record the effect to a `.tterec` file for [playback](appguide.md#recording-and-playback). |
| ++tab++ | Move between the effect list, the text, and the options. |
| ++ctrl+q++ | Quit. |

## Canvas

By default the canvas is the whole text area and text is anchored to its top left, so the effect draws your text
where you typed it. To preview an effect on a smaller canvas, set **canvas-width** and **canvas-height** on the
Canvas tab. Setting either to `-1` sizes it to the text, as the command line does by default.

The exported command includes these canvas settings when they differ from the command-line defaults, so the effect
plays the same way in your terminal.

## Input Colors

Text with ANSI colors, such as `ls --color=always` or fetch output, keeps its colors in the text area. Colors stay
attached to their characters as you edit, and text typed inside a colored word takes that word's color. Effects use
the colors when **existing-color-handling** on the Canvas tab is `always` or `dynamic`, as with
`--existing-color-handling` on the command line. When saving, choose whether to keep the colors in the file.
