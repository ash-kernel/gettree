#!/usr/bin/env python3
"""
gettree - Modern folder tree generator with enhanced features
Optimized version with improved error handling and performance
"""

import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, List, Tuple

import pathspec
import typer
from colorama import Fore, Style, init
from rich.tree import Tree
from rich import print as rprint
from rich.console import Console

# Try tomllib (Python 3.11+), fallback to tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

# Initialize colorama with Windows support
init(autoreset=True, convert=True)

# ANSI escape code pattern for stripping colors
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# Console for rich output
console = Console()

# Default patterns to ignore
DEFAULT_IGNORES = {".git", "node_modules", "dist", "build", "__pycache__", ".venv", "venv"}

# File type icons
ICONS = {
    "folder": "📁",
    "file": "📄",
    ".py": "🐍",
    ".js": "🟨",
    ".ts": "🟦",
    ".tsx": "⚛️",
    ".jsx": "⚛️",
    ".html": "🌐",
    ".css": "🎨",
    ".json": "🧩",
    ".md": "📝",
    ".txt": "📃",
    ".yaml": "⚙️",
    ".yml": "⚙️",
    ".toml": "⚙️",
    ".sh": "🔧",
    ".rs": "🦀",
    ".go": "🐹",
}


@dataclass
class TreeStats:
    """Statistics collected during tree generation."""
    files: int = 0
    folders: int = 0
    total_size: int = 0
    scan_time: float = 0.0
    max_depth: int = 0
    errors: int = 0

    def to_dict(self) -> dict:
        return {
            **asdict(self),
            "total_size_formatted": format_size(self.total_size),
            "scan_time_ms": round(self.scan_time * 1000, 2),
        }


def load_ignore_spec(
    root: Path,
    use_gitignore: bool = True,
    use_gettreeignore: bool = True,
    use_dockerignore: bool = False,
) -> Optional[pathspec.PathSpec]:
    """Load and merge ignore patterns from various ignore files."""
    patterns = []
    ignore_files = []

    if use_gitignore:
        ignore_files.append(".gitignore")
    if use_gettreeignore:
        ignore_files.append(".gettreeignore")
    if use_dockerignore:
        ignore_files.append(".dockerignore")

    for ignore_file in ignore_files:
        path = root / ignore_file
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    patterns.extend(f.read().splitlines())
            except (OSError, UnicodeDecodeError) as e:
                console.print(f"[yellow]⚠️  Warning: Could not read {ignore_file}: {e}[/yellow]")

    return pathspec.PathSpec.from_lines("gitwildmatch", patterns) if patterns else None


def load_config() -> dict:
    """Load configuration from ~/.config/gettree/config.toml."""
    if not tomllib:
        return {}

    config_path = Path.home() / ".config" / "gettree" / "config.toml"
    if not config_path.exists():
        return {}

    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        console.print(f"[yellow]⚠️  Warning: Could not load config: {e}[/yellow]")
        return {}


def strip_ansi(text: str) -> str:
    """Remove ANSI color codes from text."""
    return ANSI_ESCAPE.sub("", text)


def format_size(size: int) -> str:
    """Format byte size to human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def get_icon(name: str, is_dir: bool) -> str:
    """Get emoji icon for file/folder."""
    if is_dir:
        return ICONS["folder"]
    return ICONS.get(Path(name).suffix.lower(), ICONS["file"])


def color_name(name: str, is_dir: bool) -> str:
    """Apply color to file/folder name."""
    if is_dir:
        return f"{Fore.BLUE}{name}{Style.RESET_ALL}"

    color_map = {
        ".py": Fore.GREEN,
        ".js": Fore.YELLOW,
        ".ts": Fore.YELLOW,
        ".tsx": Fore.YELLOW,
        ".jsx": Fore.YELLOW,
        ".json": Fore.CYAN,
        ".md": Fore.MAGENTA,
        ".html": Fore.RED,
        ".css": Fore.MAGENTA,
    }

    suffix = Path(name).suffix.lower()
    color = color_map.get(suffix, "")
    return f"{color}{name}{Style.RESET_ALL}" if color else name


def should_ignore(
    item: str,
    rel_path: str,
    spec: Optional[pathspec.PathSpec],
    extra: set,
    omit_ignored: bool = True,
) -> bool:
    """Check if item should be ignored based on patterns."""
    if not omit_ignored:
        return False
    if item in DEFAULT_IGNORES or item in extra:
        return True
    if spec and spec.match_file(rel_path):
        return True
    return False


def matches_filter(name: str, filter_pattern: Optional[str], is_dir: bool) -> bool:
    """Check if name matches filter pattern (always true for directories)."""
    if not filter_pattern or is_dir:
        return True
    try:
        return re.search(filter_pattern, name, re.IGNORECASE) is not None
    except re.error:
        return True


def get_sorted_entries(path: str, sort_by: str) -> List[os.DirEntry]:
    """Get sorted directory entries using scandir for performance."""
    try:
        with os.scandir(path) as it:
            entries = list(it)
    except (PermissionError, OSError):
        return []

    # Sort directories first, then by specified criteria
    if sort_by == "size":
        return sorted(
            entries,
            key=lambda x: (
                not x.is_dir(),
                x.stat(follow_symlinks=False).st_size if not x.is_dir() else 0,
            ),
            reverse=True,
        )
    elif sort_by == "type":
        return sorted(
            entries,
            key=lambda x: (
                not x.is_dir(),
                Path(x.name).suffix.lower(),
                x.name.lower(),
            ),
        )
    else:  # name (default)
        return sorted(entries, key=lambda x: (not x.is_dir(), x.name.lower()))


def build_tree_dict(
    path_str: str,
    root_str: str,
    spec: Optional[pathspec.PathSpec],
    extra: set,
    max_depth: Optional[int],
    depth: int,
    stats: TreeStats,
    filter_pattern: Optional[str] = None,
    sort_by: str = "name",
    omit_ignored: bool = True,
) -> dict:
    """Build a dictionary representation of the tree for JSON/CSV export."""
    if max_depth is not None and depth > max_depth:
        return {}

    stats.max_depth = max(stats.max_depth, depth)
    tree_dict = {}
    entries = get_sorted_entries(path_str, sort_by)

    for entry in entries:
        try:
            rel_path = os.path.relpath(entry.path, root_str)
            is_dir = entry.is_dir(follow_symlinks=False)

            if should_ignore(entry.name, rel_path, spec, extra, omit_ignored):
                continue
            if not matches_filter(entry.name, filter_pattern, is_dir):
                continue

            if is_dir:
                stats.folders += 1
                tree_dict[entry.name] = build_tree_dict(
                    entry.path,
                    root_str,
                    spec,
                    extra,
                    max_depth,
                    depth + 1,
                    stats,
                    filter_pattern,
                    sort_by,
                    omit_ignored,
                )
            else:
                stats.files += 1
                try:
                    size = entry.stat(follow_symlinks=False).st_size
                    stats.total_size += size
                    tree_dict[entry.name] = {"__size__": size}
                except OSError:
                    tree_dict[entry.name] = {}
                    stats.errors += 1

        except (PermissionError, OSError):
            stats.errors += 1
            continue

    return tree_dict


def generate_tree(
    path_str: str,
    root_str: str,
    spec: Optional[pathspec.PathSpec],
    prefix: str,
    output: list,
    depth: int,
    max_depth: Optional[int],
    icons: bool,
    color: bool,
    size: bool,
    extra: set,
    stats: TreeStats,
    filter_pattern: Optional[str] = None,
    sort_by: str = "name",
    omit_ignored: bool = True,
) -> None:
    """Generate tree output recursively."""
    if max_depth is not None and depth > max_depth:
        return

    stats.max_depth = max(stats.max_depth, depth)
    entries = get_sorted_entries(path_str, sort_by)
    filtered = []

    for entry in entries:
        try:
            rel_path = os.path.relpath(entry.path, root_str)
            is_dir = entry.is_dir(follow_symlinks=False)

            if should_ignore(entry.name, rel_path, spec, extra, omit_ignored):
                continue
            if not matches_filter(entry.name, filter_pattern, is_dir):
                continue

            filtered.append((entry, is_dir))
        except (PermissionError, OSError):
            stats.errors += 1
            continue

    if not filtered:
        return

    # Tree branch characters
    pointers = ["├── "] * (len(filtered) - 1) + ["└── "]

    for pointer, (entry, is_dir) in zip(pointers, filtered):
        try:
            if is_dir:
                stats.folders += 1
            else:
                stats.files += 1

            icon = f"{get_icon(entry.name, is_dir)} " if icons else ""
            name = color_name(entry.name, is_dir) if color else entry.name

            if size and not is_dir:
                try:
                    file_size = entry.stat(follow_symlinks=False).st_size
                    stats.total_size += file_size
                    name += f" ({format_size(file_size)})"
                except OSError:
                    stats.errors += 1

            output.append(f"{prefix}{pointer}{icon}{name}")

            if is_dir:
                ext = "│   " if pointer == "├── " else "    "
                generate_tree(
                    entry.path,
                    root_str,
                    spec,
                    prefix + ext,
                    output,
                    depth + 1,
                    max_depth,
                    icons,
                    color,
                    size,
                    extra,
                    stats,
                    filter_pattern,
                    sort_by,
                    omit_ignored,
                )

        except (PermissionError, OSError):
            stats.errors += 1
            continue


def run_tui(
    root_str: str,
    spec: Optional[pathspec.PathSpec],
    extra: set,
    omit_ignored: bool = True,
) -> None:
    """Run interactive TUI mode with rich tree."""

    def build(path_str: str, tree: Tree) -> None:
        entries = get_sorted_entries(path_str, "name")
        for entry in entries:
            try:
                rel_path = os.path.relpath(entry.path, root_str)
                is_dir = entry.is_dir(follow_symlinks=False)

                if should_ignore(entry.name, rel_path, spec, extra, omit_ignored):
                    continue

                label = f"[bold blue]{entry.name}[/]" if is_dir else entry.name
                branch = tree.add(label)
                if is_dir:
                    build(entry.path, branch)
            except (PermissionError, OSError):
                continue

    root_name = os.path.basename(os.path.abspath(root_str))
    tree = Tree(f"[bold green]{root_name}[/]")
    build(root_str, tree)
    rprint(tree)


def export_csv(tree_dict: dict, output_path: str) -> None:
    """Export tree structure to CSV format."""
    rows = []

    def traverse(node: dict, prefix: str = ""):
        for name, value in sorted(node.items()):
            if isinstance(value, dict):
                if "__size__" in value:
                    rows.append({
                        "path": prefix + name,
                        "type": "file",
                        "size": value.get("__size__", 0),
                    })
                else:
                    rows.append({"path": prefix + name, "type": "dir", "size": ""})
                    traverse(value, prefix + name + "/")

    traverse(tree_dict)

    try:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["path", "type", "size"])
            writer.writeheader()
            writer.writerows(rows)
    except OSError as e:
        console.print(f"[red]❌ Error writing CSV file: {e}[/red]")
        raise typer.Exit(1)


def save_output(content: str, output_path: str, strip_colors: bool = True) -> None:
    """Save output to file with proper error handling."""
    try:
        final_content = strip_ansi(content) if strip_colors else content
        Path(output_path).write_text(final_content, encoding="utf-8")
        console.print(f"[green]✅ Saved to {output_path}[/green]")
    except OSError as e:
        console.print(f"[red]❌ Error writing file: {e}[/red]")
        raise typer.Exit(1)


# Create Typer app with proper configuration
app = typer.Typer(
    help="🔥 gettree - modern folder tree generator",
    add_completion=False,
    pretty_exceptions_enable=False,
)


@app.command()
def main(
    # Positional argument first (fixes help text)
    path: str = typer.Argument(
        ".",
        help="Root directory to scan",
        show_default=False,
    ),
    # Options
    output: Optional[str] = typer.Option(
        None,
        "--output", "-o",
        help="Save output to file",
    ),
    markdown: bool = typer.Option(
        False,
        "--markdown", "-m",
        help="Wrap output in markdown code block",
    ),
    json_mode: bool = typer.Option(
        False,
        "--json", "-j",
        help="Output as structured JSON",
    ),
    csv_export: bool = typer.Option(
        False,
        "--csv",
        help="Export as CSV (requires --output)",
    ),
    ignore: Optional[List[str]] = typer.Option(
        None,
        "--ignore", "-i",
        help="Additional patterns to ignore",
    ),
    filter_pattern: Optional[str] = typer.Option(
        None,
        "--filter", "-f",
        help="Filter files by regex pattern",
    ),
    sort_by: str = typer.Option(
        "name",
        "--sort",
        help="Sort by: name, size, or type",
    ),
    fullpath: bool = typer.Option(
        False,
        "--fullpath",
        help="Show absolute path for root",
    ),
    depth: Optional[int] = typer.Option(
        None,
        "--depth", "-d",
        help="Maximum depth to traverse",
    ),
    size: bool = typer.Option(
        False,
        "--size", "-s",
        help="Show file sizes",
    ),
    icons: bool = typer.Option(
        False,
        "--icons",
        help="Show emoji icons",
    ),
    color: bool = typer.Option(
        False,
        "--color", "-c",
        help="Enable colored output",
    ),
    watch: bool = typer.Option(
        False,
        "--watch", "-w",
        help="Watch mode (refresh every 2s)",
    ),
    tui: bool = typer.Option(
        False,
        "--tui",
        help="Rich interactive tree view",
    ),
    stats: bool = typer.Option(
        False,
        "--stats",
        help="Show summary statistics",
    ),
    dockerignore: bool = typer.Option(
        False,
        "--dockerignore",
        help="Include .dockerignore patterns",
    ),
    omit_ignored: Optional[bool] = typer.Option(
        None,
        "--omit-ignored/--show-ignored",
        help="Hide or show ignored files",
    ),
) -> None:
    """
    Generate a tree view of directory structure with various output formats and filtering options.
    """
    # Validate arguments
    if csv_export and not output:
        console.print("[red]❌ Error: --csv requires --output to specify destination file[/red]")
        raise typer.Exit(1)

    if sort_by not in ["name", "size", "type"]:
        console.print(f"[red]❌ Error: Invalid sort option '{sort_by}'. Use: name, size, or type[/red]")
        raise typer.Exit(1)

    # Load config with fallback
    config = load_config()

    # Apply config defaults
    use_dockerignore = dockerignore or config.get("use_dockerignore", False)
    use_color = color or config.get("color", False)
    use_icons = icons or config.get("icons", False)
    use_depth = depth if depth is not None else config.get("depth")
    use_omit_ignored = (
        omit_ignored if omit_ignored is not None else config.get("omit_ignored", True)
    )

    # Resolve and validate path
    try:
        root_path = Path(path).resolve()
        if not root_path.exists():
            console.print(f"[red]❌ Error: Path does not exist: {path}[/red]")
            raise typer.Exit(1)
        if not root_path.is_dir():
            console.print(f"[red]❌ Error: Path is not a directory: {path}[/red]")
            raise typer.Exit(1)
    except (OSError, RuntimeError) as e:
        console.print(f"[red]❌ Error resolving path: {e}[/red]")
        raise typer.Exit(1)

    root_str = str(root_path)

    def run_once() -> None:
        """Execute single tree generation."""
        scan_start = time.time()
        spec = load_ignore_spec(root_path, use_dockerignore=use_dockerignore)
        extra = set(ignore or [])
        tree_stats = TreeStats()

        # TUI mode
        if tui:
            run_tui(root_str, spec, extra, use_omit_ignored)
            return

        # JSON/CSV mode
        if json_mode or csv_export:
            tree_dict = build_tree_dict(
                root_str,
                root_str,
                spec,
                extra,
                use_depth,
                0,
                tree_stats,
                filter_pattern,
                sort_by,
                use_omit_ignored,
            )

            if csv_export:
                if not output:
                    console.print("[red]❌ CSV export requires --output option[/red]")
                    raise typer.Exit(1)
                export_csv(tree_dict, output)
                console.print(f"[green]✅ CSV exported to {output}[/green]")
                return

            # JSON output
            result = {
                "root": root_str if fullpath else root_path.name,
                "tree": tree_dict,
            }

            if stats:
                tree_stats.scan_time = time.time() - scan_start
                result["stats"] = tree_stats.to_dict()

            output_text = json.dumps(result, indent=2, ensure_ascii=False)
            typer.echo(output_text)

            if output:
                save_output(output_text, output, strip_colors=False)

            return

        # Standard tree output
        output_lines = [root_str if fullpath else root_path.name]
        generate_tree(
            root_str,
            root_str,
            spec,
            "",
            output_lines,
            0,
            use_depth,
            use_icons,
            use_color,
            size,
            extra,
            tree_stats,
            filter_pattern,
            sort_by,
            use_omit_ignored,
        )

        # Add statistics if requested
        if stats:
            tree_stats.scan_time = time.time() - scan_start
            output_lines.extend([
                "",
                "📊 Summary:",
                f"  Files: {tree_stats.files:,}",
                f"  Folders: {tree_stats.folders:,}",
                f"  Total Size: {format_size(tree_stats.total_size)}",
                f"  Max Depth: {tree_stats.max_depth}",
                f"  Scan Time: {tree_stats.scan_time * 1000:.1f}ms",
            ])
            if tree_stats.errors > 0:
                output_lines.append(f"  Errors: {tree_stats.errors} (permission denied)")

        # Wrap in markdown if requested
        if markdown:
            output_lines = ["```"] + output_lines + ["```"]

        result = "\n".join(output_lines)
        typer.echo(result)

        # Save to file if specified
        if output:
            save_output(result, output, strip_colors=True)

    # Watch mode
    if watch:
        try:
            while True:
                # Clear terminal using ANSI escape codes
                print("\033[H\033[J", end="", flush=True)
                try:
                    run_once()
                except Exception as e:
                    console.print(f"[red]Error during scan: {e}[/red]")
                time.sleep(2)
        except KeyboardInterrupt:
            console.print("\n[yellow]👋 Stopped watching[/yellow]")
            sys.exit(0)
    else:
        run_once()


if __name__ == "__main__":
    app()