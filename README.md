<div align="center">

# Gettree

<img src="https://raw.githubusercontent.com/ash-kernel/gettree/main/assets/logo.png" width="140" alt="gettree logo"/>

**A blazing fast, modern directory tree generator with smart ignores, regex filtering, and rich data exports.**

<br/>

<img src="https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white" alt="Python Version" />
<img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey" alt="Platforms" />
<img src="https://img.shields.io/badge/License-MIT-green" alt="License" />
<a href="https://pypi.org/project/gettree/">
  <img src="https://img.shields.io/pypi/v/gettree?color=orange&logo=pypi&logoColor=white" alt="PyPI Version" />
</a>

</div>

---

## Overview

`gettree` is a next-generation CLI tool designed to replace the traditional `tree` command. Built for modern developer workflows, it automatically respects your ignore files, allows complex regex filtering, sorts by size or type, and exports your directory structures into actionable data formats (JSON, CSV, Markdown).

### Why gettree?
*   **Blazing Fast:** Utilizes optimized `os.scandir()` caching to traverse massive directories in milliseconds without redundant system calls.
*   **Smart Ignores:** Natively reads `.gitignore`, `.dockerignore`, and custom `.gettreeignore` files.
*   **Beautiful UI:** Full color support, file-specific emoji icons, and a flicker-free interactive Watch Mode.
*   **Data-Ready:** Export your folder structures directly to structured JSON or CSV for downstream scripting.

---

## Installation

Available natively via PyPI.

    pip install gettree

Or install the latest bleeding-edge version directly from GitHub:

    pip install git+https://github.com/ash-kernel/gettree.git

---

## Usage

    gettree [PATH] [OPTIONS]

### Quick Start
    gettree .                                  # Basic tree
    gettree . --color --icons --stats          # Full visual experience
    gettree . --filter "\.py$"                 # Regex: Show only Python files
    gettree . --sort size --size               # Sort by size (largest first)
    gettree . --json -o tree.json              # Export structure to JSON
    gettree . --markdown -o docs/tree.md       # Export wrapped in Markdown

---

## Options

### Display & UI
| Flag | Description |
|---|---|
| `--color`, `-c` | Enable syntax-highlighted colored output. |
| `--icons` | Show file-specific emoji icons (🐍, 🌐, 📄, etc.). |
| `--size`, `-s` | Display human-readable file sizes. |
| `--depth`, `-d N` | Limit maximum folder traversal depth. |
| `--fullpath` | Show absolute paths instead of relative names. |
| `--stats` | Append a summary block (files, folders, size, scan time). |

### Output & Export
| Flag | Description |
|---|---|
| `--json` | Output as structured, nested JSON. |
| `--csv` | Export as a flat CSV file (requires `-o`). |
| `--markdown` | Wrap standard text output in a markdown code block. |
| `--output`, `-o FILE`| Save the generated output to a specific file. |

### Filtering & Sorting
| Flag | Description |
|---|---|
| `--filter`, `-f PAT` | Filter items using a Regex pattern. |
| `--sort TYPE` | Sort items by: `name`, `size`, or `type`. [Default: `name`] |
| `--ignore`, `-i PAT` | Add extra ad-hoc patterns to exclude. |
| `--show-ignored` | Force display of ignored files/folders. |

### Advanced Modes
| Flag | Description |
|---|---|
| `--watch`, `-w` | **Watch Mode:** Live-reload the tree every 2s (flicker-free). |
| `--tui` | **TUI Mode:** Open a rich, interactive tree view. |
| `--dockerignore` | Explicitly include `.dockerignore` patterns. |

---

## Ignore Rules

`gettree` prevents terminal spam by automatically ignoring heavy folders (`node_modules`, `.git`, `__pycache__`) and seamlessly reading your project's ignore rules.

Patterns are loaded and merged from:
1.  `.gitignore` (Loaded by default)
2.  `.gettreeignore` (Custom project rules, loaded by default)
3.  `.dockerignore` (Requires `--dockerignore` flag)

### Example `.gettreeignore`

    *.log
    dist/
    temp/
    secret_keys.json

---

## Configuration

Tired of typing `--color --icons` every time? Create a persistent configuration file at `~/.config/gettree/config.toml` to set your defaults.

**Priority Order:** CLI Arguments > Config File > Built-in Defaults

    # ~/.config/gettree/config.toml
    
    # Ignore Settings
    use_gitignore = true
    use_gettreeignore = true
    use_dockerignore = false
    omit_ignored = true
    
    # Display Defaults
    color = true       # Always use colors
    icons = true       # Always show icons
    depth = null       # Max depth (null = unlimited)

*(Note: Windows users can create this file at `C:\Users\YourName\.config\gettree\config.toml`)*

---

## Real-World Recipes

**Audit a massive project:**
    gettree . --sort size --size --color --depth 3 --stats

**Find all TypeScript files & save to Markdown:**
    gettree . --filter "\.tsx?$" --markdown -o frontend_structure.md

**Monitor an active build directory:**
    gettree ./dist --watch --color --stats

---

## Performance

Thanks to `os.scandir()` caching and optimized memory handling, `gettree` is built for speed:
*   **Small projects** (< 100 files): `< 5ms`
*   **Medium projects** (< 1,000 files): `5 - 50ms`
*   **Massive projects** (> 10,000 files): `50 - 500ms`

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

<div align="center">
  <b>Developed by Ash</b><br>
  <a href="https://github.com/ash-kernel">GitHub</a> • <a href="https://pypi.org/project/gettree/">PyPI</a>
</div>