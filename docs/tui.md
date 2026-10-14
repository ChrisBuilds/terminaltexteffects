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
  Type in the filter above the list to show only effects whose name or description contains every word you type,
  and press ++down++ or ++enter++ to move into the list. Highlighting an effect shows its options. Pressing ++enter++
  on it plays it.
- **The playback bar** above the text has two groups. On the left, buttons play or pause, stop, and step through the
  effect and play a random effect, with the **Loop** and **Auto** (auto-replay) toggles. On the right, **Open** and
  **Save** load and save the text, and **Fit** and **Max** size the canvas.
- **Text** fills the rest of the top of the screen. Type, paste, and arrange text here. The subtitle shows the canvas
  size, and while an effect is shown, the frame number and the frame rate.
- **Options** at the bottom has two tabs. **Effect** holds the selected effect's options, and **Canvas** holds the
  terminal options that affect previews: canvas size and anchors, text wrapping, frame rate, color handling, and tab
  width.

The interface uses a TerminalTextEffects theme in purple, cyan, and white. Other Textual themes are available from
the command palette (++ctrl+p++).

Option inputs follow each option's type: a checkbox for on/off options, a list for fixed choices such as gradient
directions and easing functions, which opens inside the options panel and scrolls, and a text box for everything else. Text boxes use the same spelling as the
command line. Lists are space separated, such as `ff0000 00ff00 0000ff`, and colors show a swatch. Hover over an
option to see its help, how to write its value with an example, and its default. An invalid value
turns its name and field red, with the reason in its tooltip, and the effect won't play until it is fixed. Changed
options have their names highlighted. Clearing a field and leaving it, or pressing ++shift+f6++ on an option,
returns that option to its default. Each effect keeps its own values while the interface is open. The
selected effect's description is shown along the bottom of the options panel.

### Picking colors

Color options open a color picker when you press ++f7++ or ++enter++ in the field, or click the swatch. Choose from
the 256 XTerm colors in the palette, type a hex value, or drag the hue, saturation, and lightness bars. Palette
colors stay XTerm colors on the command line, and any other change gives an RGB hex color. For gradient options,
the picker edits the list of stops: select a stop, change its color, and add, remove, or reorder stops while a bar
previews the gradient. Press ++ctrl+s++ or choose **Apply** to keep the colors, or ++escape++ to discard them.

## Playback

++f5++ or **Play** plays the selected effect. While it plays, ++f5++ or ++space++ pauses and resumes it, and
++right++ pauses it and shows one frame at a time. Once the effect has finished or been stopped, **Play** plays it
again from the start, as does ++ctrl+r++ at any time. ++f9++ plays a random effect from the listed effects. The effect plays on a black background. ++escape++, or a click on the effect, returns to the text, and a
click puts the cursor where you clicked.

Turn on **Loop** to replay the effect a second after it finishes. Loops replay the frames of the first run, so they
start at once, and stop reusing them when you change an option or the text. Turn on **Auto** to replay the effect
shortly after you change an option or highlight another effect, without leaving the field you are editing.

Effects build their animations and draw their frames on a background thread, a few frames ahead of the screen, so
the interface stays responsive while a large effect is prepared. The frame rate in the subtitle is the rate the
interface manages to show, next to the **frame-rate** option.

## Keys

| Key | Action |
| --- | --- |
| ++f1++ | Show the keys and a few tips. |
| ++f5++ | Play or pause the selected effect. Once it has finished, play it again from the start. |
| ++space++ / ++right++ | While an effect is shown: pause or resume it / show the next frame. |
| ++ctrl+r++ | Replay the effect from the start. |
| ++f9++ | Play a random effect. |
| ++escape++ | Stop the effect, or clear the finished effect, and return to the text. |
| ++ctrl+t++ / ++ctrl+g++ | Fit the canvas exactly around the text / grow it to the whole text area. |
| ++f2++ | Open a text file. |
| ++f3++ | Save the text to a file. |
| ++f4++ | Show the `tte` command for the current settings, or load a pasted command. |
| ++f7++ | Open the color picker for the selected color option. |
| ++shift+f6++ | Reset the focused option to its default. |
| ++f6++ | Reset the selected effect's options and the canvas options. |
| ++f8++ | Record the effect to a `.tterec` file for [playback](appguide.md#recording-and-playback). |
| ++tab++ | Move between the effect filter, the effect list, the text, and the options. |
| ++ctrl+p++ | Open the command palette, including themes. |
| ++ctrl+q++ | Quit, keeping the session for next time. |

## Canvas

By default the canvas is the whole text area and text is anchored to its top left, so the effect draws your text
where you typed it. To preview an effect on a smaller canvas, set **canvas-width** and **canvas-height** on the
Canvas tab. Setting either to `-1` sizes it to the text, as the command line does by default. **Fit** (++ctrl+t++)
sets the canvas to the size of the text, and **Max** (++ctrl+g++) sets it back to the whole text area.

A cyan outline of full blocks marks the canvas, one cell outside it, and stays visible while you edit and while
an effect plays. Text outside the canvas is dimmed because the effect won't show it. Drag the outline to resize
the canvas, and **canvas-width** and **canvas-height** update to match. The outline is drawn on the edges that move
with **anchor-canvas**: with the default `nw` anchor, the right and bottom edges. The text area keeps one free column
or row beyond each of those edges, so effects draw in a slightly smaller area than the text area, and the outline
stays visible when the canvas fills that area. Dragging an edge all the way out sets that dimension to `0`, the
whole area.

## Commands

++f4++ shows the `tte` command that plays the effect with the current options, with a button to copy it. The exported
command includes the canvas settings when they differ from the command-line defaults, so the effect plays the same
way in your terminal.

The same dialog loads a command: paste a `tte` command, such as one copied from the docs, and choose **Load**. The
interface selects its effect and applies its options. Options the command leaves out take their command-line
defaults, so the preview matches what the command plays. Its `--input-file`, if any, is opened, and flags the
interface doesn't offer, such as `--reuse-canvas`, are listed in a notice and skipped.

## Session

When you quit with ++ctrl+q++, the interface saves the selected effect, the options you changed, the text with its
colors, and the **Loop** and **Auto** toggles to `$XDG_CONFIG_HOME/terminaltexteffects/tui_session.json`, or
`~/.config/terminaltexteffects/tui_session.json` when `XDG_CONFIG_HOME` isn't set. The next start restores them.
Text you pipe in or open with `-i`, and an effect named on the command line, take the place of the saved ones.
Delete the file to start fresh.

## Files

++f2++, ++f3++, and ++f8++ open a file dialog with a folder tree and a path field. Browse the tree with the mouse or
arrow keys, or type a path. Choosing a file twice, such as with a double click, opens it. When saving, choosing a
folder keeps the file name you typed, and saving over an existing file asks for confirmation first. **Home** and
**Up** (++ctrl+up++) change folders, and **Hidden** (++ctrl+t++) shows dot files.

## Input Colors

Text with ANSI colors, such as `ls --color=always` or fetch output, keeps its colors in the text area. Colors stay
attached to their characters as you edit, and text typed inside a colored word takes that word's color. Effects use
the colors when **existing-color-handling** on the Canvas tab is `always` or `dynamic`, as with
`--existing-color-handling` on the command line. When saving, choose whether to keep the colors in the file.
