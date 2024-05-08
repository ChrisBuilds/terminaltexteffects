# Lesson 0

## Introduction to the TTE Engine

The TTE engine architecture features a single Terminal object and many, mostly isolated, EffectCharacter objects. The Terminal is responsible for creating EffectCharacters, providing them to the effects, and printing them to the screen. EffectCharacters are responsible for progressing themselves through their animation/motion logic. You can think of every character on the screen as it's own object, moving itself around, and modifying it's own appearance. The Terminal simply gets the latest location and string representation of each character on every call to Terminal.print().

### Terminal

Let's look at the lifecycle of the Terminal.

``` mermaid
---
title: Terminal
---
get_dimensions
make_effectcharacters
update_terminal_state
make_output_string
print

[*] --> get_dimensions
get_dimensions --> make_effectcharacters
make_effectcharacters --> update_terminal_state
update_terminal_state --> make_output_string
make_output_string --> print
print --> update_terminal_state
print --> [*]

```
