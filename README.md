<div align="center">

# gettree

<img src="https://raw.githubusercontent.com/ash-kernel/gettree/main/assets/logo.png" width="140"/>

**Modern tree CLI with ignore support, filtering, and exports**

<br/>

<img src="https://img.shields.io/badge/Python-CLI-blue?logo=python" />
<img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey" />
<img src="https://img.shields.io/badge/License-MIT-green" />
<a href="https://pypi.org/project/gettree/">
  <img src="https://img.shields.io/pypi/v/gettree?label=PyPI" />
</a>

</div>

---

## Overview

`gettree` is a fast CLI to visualize directory structures with:
- ignore rules
- filterings
- sorting
- multiple export formats

---

## Install

    pip install gettree

or

    pip install git+https://github.com/ash-kernel/gettree.git

---

## Usage

    gettree [path] [options]

---

## Examples

    gettree .
    gettree . --color --icons --size
    gettree . --depth 2
    gettree . --filter "\.py$"
    gettree . --sort size --size
    gettree . --json -o tree.json
    gettree . --markdown -o tree.md

---

## Features

- `.gitignore` + `.gettreeignore`
- regex filtering (`--filter`)
- sorting (`name | size | type`)
- file size + depth control
- JSON / CSV / Markdown export
- stats (files, folders, size, time)
- watch mode + TUI

---

## Options

Display:
    --color, -c
    --icons
    --size, -s
    --depth, -d N
    --fullpath
    --stats
    --dirs-only
    --files-only
    --hidden

Output:
    --json
    --csv
    --markdown
    --output, -o FILE
    --flat
    --count

Advanced:
    --filter, -f REGEX
    --sort TYPE
    --ignore, -i PATTERN
    --no-ignore
    --min-size SIZE
    --max-size SIZE
    --watch, -w
    --tui
    --no-color

---

## Ignore Rules

Supports:
    .gitignore
    .gettreeignore

Example:
    *.log
    dist/
    temp/

---

## Example Output

    src
    ├── main.py
    └── README.md

---

## License

MIT


## Author

ash-kernel 

MADE WITH ❤️

## My other works
### SpiceDeck - Your Games, One Launcher.

<a href="https://github.com/ash-kernel/spicedeck">
  <img src="https://github.com/ash-kernel/ash-kernel/blob/main/banner1.png?raw=true" width=400 />
</a>
