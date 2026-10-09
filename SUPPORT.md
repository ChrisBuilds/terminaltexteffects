# Support and compatibility

## Releases and Python versions

| Version | Minimum Python | Status |
| --- | --- | --- |
| 0.15.0, latest published stable release | 3.8 | Published package requirements |
| Development `main`, toward 0.16.0 | 3.9.2 | Upcoming requirements; not yet a published release |

Python 3.9.0 and 3.9.1 are unsupported for development `main` and the planned 0.16.0
release. Use a current patch release of a supported Python series.

CI currently tests the latest patch releases of Python 3.9 through 3.14 on Linux.
Newer Python series are unverified until they join the matrix. Older releases retain
their published installation metadata; that does not imply ongoing maintenance.
Security fixes follow the [latest-stable-release policy](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/SECURITY.md).

## Developer tooling

Documentation, release tooling, and QA hooks require Python 3.10+ on development `main`.
Use Python 3.14 for the full locked development environment. This tooling requirement
does not raise TTE's Python 3.9.2 runtime minimum; native 3.9 tests remain in CI.
The `docs` extra supplies documentation dependencies only on Python 3.10+.
On Python 3.9, installing that extra does not install a documentation toolchain.
See [CONTRIBUTING.md](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/CONTRIBUTING.md)
for separate compatibility environments.

## Operating systems and automated coverage

TTE runs on Linux, macOS, and Windows. The current automated checks cover:

| Platform | Coverage |
| --- | --- |
| Linux, Ubuntu 24.04 | Default test suite on Python 3.9–3.14 |
| macOS, macOS 15 | Focused terminal/ANSI/Unicode, configuration, CLI, and PowerShell completion tests on Python 3.14 |
| Windows, Windows Server 2025 runner | The same focused native-platform checks on Python 3.14 |

The Windows job uses native Windows Python and CLI executables. These runner versions
describe test coverage, not minimum operating-system requirements. Other OS versions
and terminal combinations may work but are not all exercised automatically. CI checks
behavior and emitted output; [release QA](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/RELEASING.md)
includes human inspection of animation, colors, wide characters, and resizing.

## Nix package coverage

Development `main` has dedicated Nix build/runtime smoke checks on Ubuntu 24.04 and
macOS 15. They test the default flake package and classic `pkgs.callPackage` against
the same locked nixpkgs input, including both installed CLI names. Each job records
its actual Nix system identifier; other architectures advertised by the flake are
unverified unless exercised by a recorded job. These checks supplement the Python
matrix and do not establish human terminal rendering correctness. Follow the root
README's Nix examples and [Nix CI guidance](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/.github/CI.md#nix-packaging-validation)
for setup, lock refresh, and reproduction. Classic builds using arbitrary local
channels may have different Python/build tooling from the tested pin.

## Terminal rendering

Use a modern terminal that supports ANSI cursor movement and color sequences. On Windows,
use Windows Terminal for animation; legacy console hosts are not a visual QA target.
The terminal renders the output, while its selected shell handles commands and completion.

RGB colors need true-color support. Try `--xterm-colors` for 256-color output or
`--no-color` to disable colors. Fonts, Unicode glyph support, character widths, terminal
size, and rendering speed can affect the result. Automated Unicode tests do not guarantee
identical display in every terminal/font combination. Use UTF-8 input, especially on Windows.

## Shell completion

Development `main` bundles Bash, Zsh, and PowerShell 7+ completion for both `tte` and
`terminaltexteffects`. PowerShell completion is planned for 0.16.0; published 0.15.0
provides Bash and Zsh completion. Setup instructions are in the
[application guide](https://chrisbuilds.github.io/terminaltexteffects/appguide/).
Completion belongs to the shell, so Windows Terminal users should select the script for
their chosen shell. Command Prompt and Windows PowerShell 5.1 completion are not covered.

## Documentation and reporting problems

The public [documentation site](https://chrisbuilds.github.io/terminaltexteffects/) follows
development `main`; a documented feature may not exist in the PyPI release you installed.
For released behavior, use the matching release tag's README and the release notes.
Documentation deployment does not publish packages. See the
[deployment policy](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/.github/DOCUMENTATION.md).

Report ordinary problems in [GitHub issues](https://github.com/ChrisBuilds/terminaltexteffects/issues).
Include TTE and Python versions, OS, terminal application and version, shell, a minimal
command or Python example, relevant flags/input, and expected versus actual output.
For visual problems, include a screenshot or recording and terminal dimensions when helpful.
Remove private data. Use the private reporting route in the security policy for vulnerabilities.
