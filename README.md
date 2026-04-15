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

### Quick Start

    gettree .                              # Basic tree
    gettree . --color --icons --stats      # With display options
    gettree . --filter "\.py$"             # Filter files
    gettree . --sort size --size           # Sort and show sizes
    gettree . --json -o tree.json          # Export to JSON
    gettree . --markdown -o tree.md        # Export to Markdown

---

## Features

- `.gitignore` + `.gettreeignore` + `.dockerignore` support
- Regex filtering (`--filter`)
- Sorting by name, size, or type
- File size display + depth control
- JSON / CSV / Markdown export
- Statistics (files, folders, size, scan time)
- Watch mode + Interactive TUI
- Config file support (`~/.config/gettree/config.toml`)
- Windows + Linux compatible

---

## Options

**Display:**
- `--color, -c` - Enable colored output
- `--icons` - Show emoji icons
- `--size, -s` - Display file sizes
- `--depth, -d N` - Maximum traversal depth
- `--fullpath` - Show absolute paths
- `--stats` - Show summary statistics

**Output Formats:**
- `--json` - Output as structured JSON
- `--csv` - Export as CSV (use with -o)
- `--markdown` - Wrap in markdown code block
- `--output, -o FILE` - Save to file

**Filtering & Sorting:**
- `--filter, -f PATTERN` - Filter by regex pattern
- `--sort TYPE` - Sort by: name|size|type [default: name]
- `--ignore, -i PATTERN` - Extra patterns to exclude

**Ignore Rules:**
- `--dockerignore` - Include .dockerignore patterns (disabled by default)

**Advanced:**
- `--watch, -w` - Watch mode (refresh every 2s)
- `--tui` - Rich interactive tree view

---

## Ignore Rules

Automatically loads and merges patterns from:

- `.gitignore` - Standard git ignore rules (loaded by default)
- `.gettreeignore` - Custom project-specific rules (loaded by default)
- `.dockerignore` - Docker ignore rules (use `--dockerignore` to enable)

### Example .gettreeignore
```
*.log
dist/
temp/
*.tmp
```

---

## Configuration

Create `~/.config/gettree/config.toml` to set defaults:

```toml
# Ignore Files
use_gitignore = true
use_gettreeignore = true
use_dockerignore = false

# Display Options
color = true       # Enable colors by default
icons = false      # Show icons by default
depth = null       # Max depth (null = unlimited)
```

**Priority:** CLI arguments > config file > built-in defaults

### Setup:
```bash
mkdir -p ~/.config/gettree
touch ~/.config/gettree/config.toml
```

Then edit the config file with your preferred defaults.

---

## Real-World Examples

**View project structure:**
```bash
gettree .
gettree . --depth 2
```

**With visuals:**
```bash
gettree . --color --icons --size --stats
```

**Find all Python files:**
```bash
gettree . --filter "\.py$" --color --icons
```

**Export for documentation:**
```bash
gettree . --markdown --depth 3 -o STRUCTURE.md
gettree . --json --stats -o structure.json
```

**Monitor during development:**
```bash
gettree . --watch --color --stats
```

**Docker-aware tree:**
```bash
gettree . --dockerignore --color --icons
```

**Sort by file size (largest first):**
```bash
gettree . --sort size --size --color --depth 2
```

---

## Example Output

```
Project
├── 📁 src
│   ├── 🐍 main.py (2.3KB)
│   └── 🐍 utils.py (1.1KB)
├── 📁 tests
│   └── 🐍 test_main.py (890B)
├── 📝 README.md (5.6KB)
└── 📄 pyproject.toml (569B)

📊 Summary:
  Files: 4
  Folders: 2
  Total Size: 9.8KB
  Scan Time: 2.1ms
```

---

## Performance

- Small projects (<100 files): <5ms
- Medium projects (<1000 files): 5-50ms
- Large projects (>1000 files): 50-500ms

---

## License

MIT

---

## Author

**ash-kernel** - [GitHub](https://github.com/ash-kernel)

Made with ❤️
