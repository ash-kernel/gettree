import csv
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import pathspec
import typer
from colorama import Fore, Style, init
from rich.tree import Tree
from rich import print as rprint

# Try tomllib (Python 3.11+), fallback to tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

# IMPORTANT: convert=True fixes Windows color issues
init(autoreset=True, convert=True)

# ANSI escape code pattern for stripping colors from file output
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

app = typer.Typer(
    help="🔥 gettree - modern folder tree generator",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

DEFAULT_IGNORES = {".git", "node_modules", "dist", "build", "__pycache__"}

ICONS = {
    "folder": "📁",
    "file": "📄",
    ".py": "🐍",
    ".js": "🟨",
    ".ts": "🟦",
    ".html": "🌐",
    ".css": "🎨",
    ".json": "🧩",
    ".md": "📝"
}


class TreeStats:
    """Track statistics during tree generation."""
    def __init__(self):
        self.files = 0
        self.folders = 0
        self.total_size = 0
        self.scan_time = 0.0
        self.max_depth_reached = 0

    def to_dict(self):
        return {
            "files": self.files,
            "folders": self.folders,
            "total_size": self.total_size,
            "total_size_formatted": format_size(self.total_size),
            "scan_time_ms": round(self.scan_time * 1000, 2),
            "max_depth": self.max_depth_reached
        }


def load_ignore_spec(root: Path, use_gitignore: bool = True, use_gettreeignore: bool = True, 
                     use_dockerignore: bool = False) -> Optional[pathspec.PathSpec]:
    """Load and merge ignore patterns from .gitignore, .gettreeignore, and .dockerignore."""
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
                patterns.extend(path.read_text().splitlines())
            except Exception:
                pass
    
    if patterns:
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    return None


def load_config() -> dict:
    """Load config from ~/.config/gettree/config.toml"""
    if not tomllib:
        return {}
    
    config_path = Path.home() / ".config" / "gettree" / "config.toml"
    if not config_path.exists():
        return {}
    
    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def strip_ansi(text: str) -> str:
    """Remove ANSI color codes from text."""
    return ANSI_ESCAPE.sub("", text)


def format_size(size: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def get_icon(name: str, is_dir: bool) -> str:
    """Get emoji icon for file/folder."""
    if is_dir:
        return ICONS["folder"]
    ext = Path(name).suffix
    return ICONS.get(ext, ICONS["file"])


def color_name(name: str, is_dir: bool) -> str:
    """Apply color coding to name based on type."""
    if is_dir:
        return Fore.BLUE + name + Style.RESET_ALL
    
    ext = Path(name).suffix
    color_map = {
        ".py": Fore.GREEN,
        ".js": Fore.YELLOW,
        ".ts": Fore.YELLOW,
        ".json": Fore.CYAN,
        ".md": Fore.MAGENTA,
    }
    
    if ext in color_map:
        return color_map[ext] + name + Style.RESET_ALL
    return name


def should_ignore(item: str, rel_path: str, spec: Optional[pathspec.PathSpec], extra: set) -> bool:
    """Check if item should be ignored."""
    if item in DEFAULT_IGNORES or item in extra:
        return True
    if spec and spec.match_file(rel_path):
        return True
    return False


def matches_filter(name: str, filter_pattern: Optional[str], is_dir: bool) -> bool:
    """Check if name matches filter pattern. Directories always match (for traversal)."""
    if not filter_pattern:
        return True
    if is_dir:
        return True  # Always traverse directories
    try:
        return re.search(filter_pattern, name, re.IGNORECASE) is not None
    except re.error:
        return True


def sort_items(items: list, sort_by: str = "name") -> list:
    """Sort items by name, size, or type."""
    if sort_by == "size":
        return sorted(items, key=lambda x: x.stat().st_size if x.is_file() else 0, reverse=True)
    elif sort_by == "type":
        return sorted(items, key=lambda x: (not x.is_dir(), x.name.lower()))
    else:  # name (default) - dirs first
        return sorted(items, key=lambda x: (not x.is_dir(), x.name.lower()))


def build_tree_dict(path: Path, root: Path, spec: Optional[pathspec.PathSpec], 
                    extra: set, max_depth: Optional[int], depth: int, 
                    stats: TreeStats, filter_pattern: Optional[str] = None,
                    sort_by: str = "name") -> dict:
    """Build tree structure as dictionary for JSON export."""
    if max_depth is not None and depth > max_depth:
        return {}
    
    stats.max_depth_reached = max(stats.max_depth_reached, depth)
    
    try:
        items = sort_items(path.iterdir(), sort_by)
    except (PermissionError, OSError):
        return {}
    
    tree_dict = {}
    
    for item in items:
        rel_path = str(item.relative_to(root))
        is_dir = item.is_dir()
        
        if should_ignore(item.name, rel_path, spec, extra):
            continue
        
        if not matches_filter(item.name, filter_pattern, is_dir):
            continue
        
        if is_dir:
            stats.folders += 1
            tree_dict[item.name] = build_tree_dict(
                item, root, spec, extra, max_depth, depth + 1, stats, filter_pattern, sort_by
            )
        else:
            stats.files += 1
            try:
                size = item.stat().st_size
                stats.total_size += size
                tree_dict[item.name] = {"__size__": size}
            except OSError:
                tree_dict[item.name] = {}
    
    return tree_dict


def generate_tree(path: Path, root: Path, spec: Optional[pathspec.PathSpec], 
                  prefix: str, output: list, depth: int, max_depth: Optional[int],
                  icons: bool, color: bool, size: bool, extra: set, 
                  stats: TreeStats, filter_pattern: Optional[str] = None,
                  sort_by: str = "name") -> None:
    """Generate tree output with text formatting."""
    if max_depth is not None and depth > max_depth:
        return
    
    stats.max_depth_reached = max(stats.max_depth_reached, depth)
    
    try:
        items = sort_items(path.iterdir(), sort_by)
    except (PermissionError, OSError):
        return
    
    filtered = []
    for item in items:
        rel_path = str(item.relative_to(root))
        if should_ignore(item.name, rel_path, spec, extra):
            continue
        is_dir = item.is_dir()
        if matches_filter(item.name, filter_pattern, is_dir):
            filtered.append(item)
    
    if not filtered:
        return
    
    pointers = ["├── "] * (len(filtered) - 1) + ["└── "]
    
    for pointer, item in zip(pointers, filtered):
        is_dir = item.is_dir()
        
        if is_dir:
            stats.folders += 1
        else:
            stats.files += 1
        
        # Build display name
        icon = f"{get_icon(item.name, is_dir)} " if icons else ""
        name = item.name
        
        if color:
            name = color_name(name, is_dir)
        
        if size and not is_dir:
            try:
                file_size = item.stat().st_size
                stats.total_size += file_size
                name += f" ({format_size(file_size)})"
            except OSError:
                pass
        
        line = prefix + pointer + icon + name
        output.append(line)
        
        if is_dir:
            ext = "│   " if pointer == "├── " else "    "
            generate_tree(item, root, spec, prefix + ext, output, 
                         depth + 1, max_depth, icons, color, size, extra, stats, 
                         filter_pattern, sort_by)


def run_tui(root: Path, spec: Optional[pathspec.PathSpec], extra: set) -> None:
    """Display tree in rich TUI format."""
    def build(path: Path, tree: Tree) -> None:
        try:
            items = sorted(path.iterdir())
        except (PermissionError, OSError):
            return
        
        for item in items:
            rel_path = str(item.relative_to(root))
            if should_ignore(item.name, rel_path, spec, extra):
                continue
            
            label = f"[bold blue]{item.name}[/]" if item.is_dir() else item.name
            branch = tree.add(label)
            
            if item.is_dir():
                build(item, branch)
    
    tree = Tree(f"[bold green]{root.name}[/]")
    build(root, tree)
    rprint(tree)


def export_csv(tree_dict: dict, root_name: str, output_path: str, parent: str = "") -> None:
    """Export tree structure to CSV format."""
    rows = []
    
    def traverse(node: dict, prefix: str = ""):
        for name, value in sorted(node.items()):
            if isinstance(value, dict):
                if "__size__" in value:
                    # File
                    rows.append({
                        "path": prefix + name,
                        "type": "file",
                        "size": value.get("__size__", 0)
                    })
                else:
                    # Directory
                    rows.append({
                        "path": prefix + name,
                        "type": "dir",
                        "size": ""
                    })
                    traverse(value, prefix + name + "/")
    
    traverse(tree_dict)
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "type", "size"])
        writer.writeheader()
        writer.writerows(rows)


@app.command()
def main(
    path: str = typer.Argument(".", help="Root directory to scan"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save output to file"),
    markdown: bool = typer.Option(False, "--markdown", help="Wrap output in markdown code block"),
    json_mode: bool = typer.Option(False, "--json", help="Output as structured JSON"),
    csv_export: bool = typer.Option(False, "--csv", help="Export as CSV (use with -o)"),
    ignore: Optional[list[str]] = typer.Option(None, "--ignore", "-i", help="Extra patterns to ignore"),
    filter_pattern: Optional[str] = typer.Option(None, "--filter", "-f", help="Filter by regex pattern"),
    sort_by: str = typer.Option("name", "--sort", help="Sort by: name|size|type"),
    fullpath: bool = typer.Option(False, "--fullpath", help="Show absolute paths"),
    depth: Optional[int] = typer.Option(None, "--depth", "-d", help="Maximum depth to traverse"),
    size: bool = typer.Option(False, "--size", "-s", help="Show file sizes"),
    icons: bool = typer.Option(False, "--icons", help="Show emoji icons"),
    color: bool = typer.Option(False, "--color", "-c", help="Enable colored output"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Watch mode (refresh every 2s)"),
    tui: bool = typer.Option(False, "--tui", help="Rich interactive tree view"),
    stats: bool = typer.Option(False, "--stats", help="Show summary statistics"),
    dockerignore: bool = typer.Option(False, "--dockerignore", help="Include .dockerignore patterns"),
) -> None:
    """Generate and display folder trees with advanced features."""
    
    # Load config file
    config = load_config()
    
    # Merge: CLI > config > defaults
    use_dockerignore = dockerignore or config.get("use_dockerignore", False)
    use_color = color or config.get("color", False)
    use_icons = icons or config.get("icons", False)
    use_depth = depth if depth is not None else config.get("depth", None)
    
    def run_once():
        root = Path(path).resolve()
        
        if not root.exists():
            typer.echo("❌ Path does not exist")
            raise typer.Exit(1)
        
        scan_start = time.time()
        spec = load_ignore_spec(root, use_dockerignore=use_dockerignore)
        extra = set(ignore or [])
        tree_stats = TreeStats()
        
        if tui:
            run_tui(root, spec, extra)
            return
        
        if json_mode:
            tree_dict = build_tree_dict(root, root, spec, extra, use_depth, 1, tree_stats, 
                                       filter_pattern, sort_by)
            result = {
                "root": str(root) if fullpath else root.name,
                "tree": tree_dict,
            }
            if stats:
                tree_stats.scan_time = time.time() - scan_start
                result["stats"] = tree_stats.to_dict()
            
            output_text = json.dumps(result, indent=2)
            
            typer.echo(output_text)
            if output:
                if csv_export:
                    export_csv(tree_dict, root.name, output)
                    typer.echo(f"\n✅ Exported to {output} (CSV)")
                else:
                    Path(output).write_text(output_text, encoding="utf-8")
                    typer.echo(f"\n✅ Saved to {output} (JSON)")
            return
        
        # Text mode
        output_lines = []
        header = str(root) if fullpath else root.name
        output_lines.append(header)
        
        generate_tree(root, root, spec, "", output_lines, 1, use_depth, 
                     use_icons, use_color, size, extra, tree_stats, filter_pattern, sort_by)
        
        if stats:
            tree_stats.scan_time = time.time() - scan_start
            output_lines.append("")
            output_lines.append("📊 Summary:")
            output_lines.append(f"  Files: {tree_stats.files}")
            output_lines.append(f"  Folders: {tree_stats.folders}")
            output_lines.append(f"  Total Size: {format_size(tree_stats.total_size)}")
            output_lines.append(f"  Max Depth: {tree_stats.max_depth_reached}")
            output_lines.append(f"  Scan Time: {tree_stats.scan_time * 1000:.1f}ms")
        
        if markdown:
            output_lines = ["```"] + output_lines + ["```"]
        
        result = "\n".join(output_lines)
        typer.echo(result)
        
        if output:
            # Strip ANSI codes when writing to file
            clean_result = strip_ansi(result)
            Path(output).write_text(clean_result, encoding="utf-8")
            typer.echo(f"\n✅ Saved to {output}")
    
    if watch:
        try:
            while True:
                os.system("cls" if os.name == "nt" else "clear")
                run_once()
                time.sleep(2)
        except KeyboardInterrupt:
            typer.echo("\n👋 Stopped watching")
    else:
        run_once()


if __name__ == "__main__":
    app()