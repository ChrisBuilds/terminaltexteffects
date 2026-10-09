#!/usr/bin/env bash
# Validate the locked flake and classic package without changing the lockfile.
set -Eeuo pipefail
report_failure() {
  printf 'Nix verification failed at line %s (exit %s)\n' "$1" "$2" >&2
}
trap 'report_failure "$LINENO" "$?"' ERR

root=$(cd "$(dirname "$0")/.." && pwd -P)
scratch=$(mktemp -d "${TMPDIR:-/tmp}/tte-nix.XXXXXX")
# macOS TMPDIR can use /var, a symlink to /private/var. Nix resolves paths
# while importing default.nix, so filter prefixes need the same physical path.
scratch=$(cd "$scratch" && pwd -P)
trap 'rm -rf "$scratch"' EXIT
cd "$root"

nix --version
system=$(nix eval --impure --raw --expr builtins.currentSystem)
printf 'Tested revision: %s\nNix system: %s\n' "$(git rev-parse HEAD)" "$system"
cp flake.lock "$scratch/flake.lock"
nix flake check --no-update-lock-file
nix build .#default --no-update-lock-file --out-link "$scratch/flake-package"
nixpkgs=$(nix eval --impure --raw --no-update-lock-file \
  --expr '(builtins.getFlake (toString ./.)).inputs.nixpkgs.outPath')

package_expression='{ source, nixpkgs }: let
  pkgs = import (builtins.toPath nixpkgs) {};
in pkgs.callPackage (builtins.toPath (source + "/default.nix")) {}'
nix-build --expr "$package_expression" --argstr source "$root" \
  --argstr nixpkgs "$nixpkgs" --out-link "$scratch/classic-package"

# Compare a clean copy of the exact filtered source with a dirty local checkout.
source_expression='{ source, nixpkgs }: let
  pkgs = import (builtins.toPath nixpkgs) {};
in toString (pkgs.callPackage (builtins.toPath (source + "/default.nix")) {}).src'
source_path() {
  nix-instantiate --eval --read-write-mode --strict --json --expr "$source_expression" \
    --argstr source "$1" --argstr nixpkgs "$nixpkgs" | python3 -c 'import json,sys; print(json.load(sys.stdin))'
}
original=$(source_path "$root")
mkdir "$scratch/clean" "$scratch/dirty"
cp -R "$original/." "$scratch/clean/"
chmod -R u+w "$scratch/clean"
cp "$root/default.nix" "$scratch/clean/default.nix"
cp -R "$scratch/clean/." "$scratch/dirty/"
for directory in .git .venv site dist .pytest_cache .ruff_cache dev_effects terminaltexteffects/__pycache__; do
  mkdir -p "$scratch/dirty/$directory"
  printf 'ignored development artifact\n' > "$scratch/dirty/$directory/fixture"
done
for file in .env .coverage terminaltexteffects/local.pyc terminaltexteffects/local.pyo \
  terminaltexteffects/effects/effect_dev.py terminaltexteffects/edit.swp terminaltexteffects/edit~; do
  printf 'ignored development artifact\n' > "$scratch/dirty/$file"
done
clean=$(source_path "$scratch/clean")
dirty=$(source_path "$scratch/dirty")
printf 'Source identities:\n  checkout: %s\n  clean: %s\n  dirty: %s\n' "$original" "$clean" "$dirty"
if ! [[ "$original" == "$clean" && "$original" == "$dirty" ]]; then
  printf 'Source identity mismatch; inspecting file differences.\n' >&2
  diff -qr "$original" "$clean"
  diff -qr "$original" "$dirty"
  exit 1
fi
printf '\nSource identity regression fixture\n' >> "$scratch/clean/README.md"
test "$original" != "$(source_path "$scratch/clean")"
test -f "$original/pyproject.toml"
test -f "$original/terminaltexteffects/__main__.py"
test -f "$original/terminaltexteffects/completions/tte.bash"
printf 'Filtered source identity stable: %s\n' "$original"

mkdir "$scratch/outside"
cd "$scratch/outside"
# Commands must use the installed wrappers, with no checkout/configuration imports.
unset PYTHONPATH PYTHONHOME TTE_DEV_EFFECTS_DIR
export XDG_CONFIG_HOME="$scratch/empty-config"
for package in "$scratch/flake-package" "$scratch/classic-package"; do
  python3 - "$package" "$root" <<'PY'
import pathlib
import subprocess
import sys

package = pathlib.Path(sys.argv[1]).resolve()
checkout = pathlib.Path(sys.argv[2]).resolve()
assert str(package).startswith('/nix/store/'), package
assert checkout not in pathlib.Path.cwd().parents and pathlib.Path.cwd() != checkout
outputs = []
for entry in ('tte', 'terminaltexteffects'):
    command = str(package / 'bin' / entry)
    help_result = subprocess.run([command, '--help'], capture_output=True, text=True, check=True, timeout=30)
    assert 'wipe' in help_result.stdout, help_result.stdout
    result = subprocess.run(
        [command, '--seed', '102', '--frame-rate', '0', '--no-color',
         '--canvas-width', '2', '--canvas-height', '1', '--ignore-terminal-dimensions',
         'wipe', '--final-gradient-stops', 'ffffff', '--final-gradient-steps', '1',
         '--final-gradient-frames', '1'],
        input='OK', capture_output=True, text=True, check=True, timeout=30,
    )
    assert 'OK' in result.stdout, result.stdout
    assert '\x1b[?25l' in result.stdout and '\x1b[?25h' in result.stdout, result.stdout
    outputs.append(result.stdout)
    print(f'{command}: help, seeded rendering, and cursor restoration passed')
assert outputs[0] == outputs[1], 'CLI aliases produced different seeded output'
PY
done
nix run "$root" --no-update-lock-file -- --help > "$scratch/run-help"
grep -q wipe "$scratch/run-help"
# Shell variables below intentionally expand in the child Bash process.
# shellcheck disable=SC2016
nix shell "$root" --no-update-lock-file --command bash -c \
  'set -eu; test "$(command -v tte)" = "$1/bin/tte"; tte --help' bash \
  "$(cd "$scratch/flake-package" && pwd -P)" > "$scratch/shell-help"
grep -q wipe "$scratch/shell-help"
cmp "$scratch/flake.lock" "$root/flake.lock"
printf 'Flake run/shell, classic build, and unchanged lockfile passed.\n'

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  {
    # Backticks are literal Markdown formatting, not command substitutions.
    # shellcheck disable=SC2016
    printf '### Nix validation\n\n- Revision: `%s`\n- System: `%s`\n' "$(git -C "$root" rev-parse HEAD)" "$system"
    # shellcheck disable=SC2016
    printf -- '- Version: `%s`\n' "$(nix --version)"
    printf -- '- Flake/classic builds, source filtering, both CLI aliases, seeded rendering, cursor restoration, run/shell, and unchanged lockfile: passed.\n'
    printf -- '- Other advertised architectures and human terminal rendering: not inspected by this job.\n'
  } >> "$GITHUB_STEP_SUMMARY"
fi
