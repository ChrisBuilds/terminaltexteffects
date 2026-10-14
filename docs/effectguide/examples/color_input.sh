#!/usr/bin/env bash
# Eight lines: the first word is red, green, and blue; the second word has no color.
for _ in 1 2 3 4 5 6 7 8; do
    printf '\033[38;2;255;80;80mTerminal\033[38;2;80;220;80mText\033[38;2;80;140;255mEffects\033[0m TerminalTextEffects\n'
done > color_input.txt
