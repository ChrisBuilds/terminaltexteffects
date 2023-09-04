<br/>
<p align="center">
  <a href="https://github.com/ChrisBuilds/terminaltexteffects">
    <img src="" alt="Logo" width="80" height="80">
  </a>

  <h3 align="center">Terminal Text Effects</h3>

  <p align="center">
    Inline Visual Effects in the Terminal
    <br/>
    <br/>
  </p>
</p>

![License](https://img.shields.io/github/license/ChrisBuilds/terminaltexteffects) 

## Table Of Contents

* [About the Project](#about-the-project)
* [Built With](#built-with)
* [Installation](#installation)
* [Usage](#usage)
* [License](#license)


## About The Project

![Screen Shot](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/tte_terminal_header.gif)

TerminalTextEffects is a collection of visual effects that run inline in the terminal. The underlying visual effect framework supports the following:
- XTerm 256 Color
- RGB Hex Triplet Color
- Color Gradients
- Character Motion
- UTF8 Character Set

## Built With

TerminalTextEffects is written in Python and does not require any 3rd party modules. Terminal interactions use standard ANSI terminal sequences and should work in most modern terminals. 

### Installation


```pip install terminaltexteffects```

## Usage

```cat your_text | tte <effect> [options]```


## License

Distributed under the MIT License. See [LICENSE](https://github.com/ChrisBuilds/terminaltexteffects/blob/main/LICENSE.md) for more information.
