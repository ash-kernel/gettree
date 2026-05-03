import csv
import json
import os
import re
import time
from pathlib import Path
from typing import Optional, List

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
    help="🔥 gettree - modern folder tree generator (God Mode)",
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
    """Load and merge ignore patterns."""
    patterns = []
    ignore_files = []
    
    if use_gitignore: ignore_files.append(".gitignore")
    if use_gettreeignore: ignore_files.append(".gettreeignore")
    if use_dockerignore: ignore_files.append(".dockerignore")
    
    for ignore_file in ignore_files:
        path = root / ignore_file
        if path.exists():
            try:
                patterns.extend(path.read_text().splitlines())
            except OSError:
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
    except OSError:
        return {}


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE.sub("", text)


def format_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def get_icon(name: str, is_dir: bool) -> str:
    if is_dir: return ICONS["folder"]
    return ICONS.get(Path(name).suffix, ICONS["file"])


def color_name(name: str, is_dir: bool) -> str:
    if is_dir: return Fore.BLUE + name + Style.RESET_ALL
    color_map = {
        ".py": Fore.GREEN, ".js": Fore.YELLOW, ".ts": Fore.YELLOW,
        ".json": Fore.CYAN, ".md": Fore.MAGENTA,
    }
    return color_map.get(Path(name).suffix, "") + name + Style.RESET_ALL if Path(name).suffix in color_map else name


def should_ignore(item: str, rel_path: str, spec: Optional[pathspec.PathSpec], extra: set, omit_ignored: bool = True) -> bool:
    if not omit_ignored: return False
    if item in DEFAULT_IGNORES or item in extra: return True
    if spec and spec.match_file(rel_path): return True
    return False


def matches_filter(name: str, filter_pattern: Optional[str], is_dir: bool) -> bool:
    if not filter_pattern or is_dir: return True
    try:
        return re.search(filter_pattern, name, re.IGNORECASE) is not None
    except re.error:
        return True


def get_sorted_entries(path: str, sort_by: str) -> List[os.DirEntry]:
    """Optimized directory fetching and sorting using cached DirEntry attributes."""
    try:
        with os.scandir(path) as it:
            entries = list(it)
    except (PermissionError, OSError):
        return []

    if sort_by == "size":
        return sorted(entries, key=lambda x: x.stat(follow_symlinks=False).st_size if not x.is_dir() else 0, reverse=True)
    elif sort_by == "type":
        return sorted(entries, key=lambda x: (not x.is_dir(), x.name.lower()))
    else:  # name
        return sorted(entries, key=lambda x: (not x.is_dir(), x.name.lower()))


def build_tree_dict(path_str: str, root_str: str, spec: Optional[pathspec.PathSpec], 
                    extra: set, max_depth: Optional[int], depth: int, 
                    stats: TreeStats, filter_pattern: Optional[str] = None,
                    sort_by: str = "name", omit_ignored: bool = True) -> dict:
    
    if max_depth is not None and depth > max_depth: return {}
    stats.max_depth_reached = max(stats.max_depth_reached, depth)
    
    tree_dict = {}
    entries = get_sorted_entries(path_str, sort_by)
    
    for entry in entries:
        rel_path = os.path.relpath(entry.path, root_str)
        is_dir = entry.is_dir(follow_symlinks=False)
        
        if should_ignore(entry.name, rel_path, spec, extra, omit_ignored): continue
        if not matches_filter(entry.name, filter_pattern, is_dir): continue
        
        if is_dir:
            stats.folders += 1
            tree_dict[entry.name] = build_tree_dict(
                entry.path, root_str, spec, extra, max_depth, depth + 1, stats, filter_pattern, sort_by, omit_ignored
            )
        else:
            stats.files += 1
            try:
                size = entry.stat(follow_symlinks=False).st_size
                stats.total_size += size
                tree_dict[entry.name] = {"__size__": size}
            except OSError:
                tree_dict[entry.name] = {}
                
    return tree_dict


def generate_tree(path_str: str, root_str: str, spec: Optional[pathspec.PathSpec], 
                  prefix: str, output: list, depth: int, max_depth: Optional[int],
                  icons: bool, color: bool, size: bool, extra: set, 
                  stats: TreeStats, filter_pattern: Optional[str] = None,
                  sort_by: str = "name", omit_ignored: bool = True) -> None:
                  
    if max_depth is not None and depth > max_depth: return
    stats.max_depth_reached = max(stats.max_depth_reached, depth)
    
    entries = get_sorted_entries(path_str, sort_by)
    filtered = []
    
    for entry in entries:
        rel_path = os.path.relpath(entry.path, root_str)
        is_dir = entry.is_dir(follow_symlinks=False)
        if not should_ignore(entry.name, rel_path, spec, extra, omit_ignored) and matches_filter(entry.name, filter_pattern, is_dir):
            filtered.append((entry, is_dir))
    
    if not filtered: return
    pointers = ["├── "] * (len(filtered) - 1) + ["└── "]
    
    for pointer, (entry, is_dir) in zip(pointers, filtered):
        if is_dir: stats.folders += 1
        else: stats.files += 1
        
        icon = f"{get_icon(entry.name, is_dir)} " if icons else ""
        name = color_name(entry.name, is_dir) if color else entry.name
        
        if size and not is_dir:
            try:
                file_size = entry.stat(follow_symlinks=False).st_size
                stats.total_size += file_size
                name += f" ({format_size(file_size)})"
            except OSError:
                pass
        
        output.append(prefix + pointer + icon + name)
        
        if is_dir:
            ext = "│   " if pointer == "├── " else "    "
            generate_tree(entry.path, root_str, spec, prefix + ext, output, 
                         depth + 1, max_depth, icons, color, size, extra, stats, 
                         filter_pattern, sort_by, omit_ignored)


def run_tui(root_str: str, spec: Optional[pathspec.PathSpec], extra: set, omit_ignored: bool = True) -> None:
    def build(path_str: str, tree: Tree) -> None:
        entries = get_sorted_entries(path_str, "name")
        for entry in entries:
            rel_path = os.path.relpath(entry.path, root_str)
            is_dir = entry.is_dir(follow_symlinks=False)
            
            if should_ignore(entry.name, rel_path, spec, extra, omit_ignored): continue
            
            label = f"[bold blue]{entry.name}[/]" if is_dir else entry.name
            branch = tree.add(label)
            if is_dir: build(entry.path, branch)
            
    root_name = os.path.basename(os.path.abspath(root_str))
    tree = Tree(f"[bold green]{root_name}[/]")
    build(root_str, tree)
    rprint(tree)


def export_csv(tree_dict: dict, root_name: str, output_path: str, parent: str = "") -> None:
    rows = []
    def traverse(node: dict, prefix: str = ""):
        for name, value in sorted(node.items()):
            if isinstance(value, dict):
                if "__size__" in value:
                    rows.append({"path": prefix + name, "type": "file", "size": value.get("__size__", 0)})
                else:
                    rows.append({"path": prefix + name, "type": "dir", "size": ""})
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
    ignore: Optional[List[str]] = typer.Option(None, "--ignore", "-i", help="Extra patterns to ignore"),
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
    omit_ignored: Optional[bool] = typer.Option(None, "--omit-ignored/--show-ignored", help="Hide/show ignored files"),
) -> None:
    config = load_config()
    
    use_dockerignore = dockerignore or config.get("use_dockerignore", False)
    use_color = color or config.get("color", False)
    use_icons = icons or config.get("icons", False)
    use_depth = depth if depth is not None else config.get("depth", None)
    use_omit_ignored = omit_ignored if omit_ignored is not None else config.get("omit_ignored", True)
    
    root_path = Path(path).resolve()
    if not root_path.exists():
        typer.echo("❌ Path does not exist")
        raise typer.Exit(1)
        
    root_str = str(root_path)

    def run_once():
        scan_start = time.time()
        spec = load_ignore_spec(root_path, use_dockerignore=use_dockerignore)
        extra = set(ignore or [])
        tree_stats = TreeStats()
        
        if tui:
            run_tui(root_str, spec, extra, use_omit_ignored)
            return
            
        if json_mode:
            tree_dict = build_tree_dict(root_str, root_str, spec, extra, use_depth, 1, tree_stats, 
                                       filter_pattern, sort_by, use_omit_ignored)
            result = {
                "root": root_str if fullpath else root_path.name,
                "tree": tree_dict,
            }
            if stats:
                tree_stats.scan_time = time.time() - scan_start
                result["stats"] = tree_stats.to_dict()
            
            output_text = json.dumps(result, indent=2)
            typer.echo(output_text)
            
            if output:
                if csv_export:
                    export_csv(tree_dict, root_path.name, output)
                    typer.echo(f"\n✅ Exported to {output} (CSV)")
                else:
                    Path(output).write_text(output_text, encoding="utf-8")
                    typer.echo(f"\n✅ Saved to {output} (JSON)")
            return

        output_lines = [root_str if fullpath else root_path.name]
        generate_tree(root_str, root_str, spec, "", output_lines, 1, use_depth, 
                     use_icons, use_color, size, extra, tree_stats, filter_pattern, sort_by, use_omit_ignored)
        
        if stats:
            tree_stats.scan_time = time.time() - scan_start
            output_lines.extend([
                "", "📊 Summary:",
                f"  Files: {tree_stats.files}",
                f"  Folders: {tree_stats.folders}",
                f"  Total Size: {format_size(tree_stats.total_size)}",
                f"  Max Depth: {tree_stats.max_depth_reached}",
                f"  Scan Time: {tree_stats.scan_time * 1000:.1f}ms"
            ])
            
        if markdown:
            output_lines = ["```"] + output_lines + ["```"]
            
        result = "\n".join(output_lines)
        typer.echo(result)
        
        if output:
            Path(output).write_text(strip_ansi(result), encoding="utf-8")
            typer.echo(f"\n✅ Saved to {output}")

    if watch:
        try:
            while True:
                # Fast, flicker-free terminal clear using ANSI escape codes
                print("\033[H\033[J", end="")
                run_once()
                time.sleep(2)
        except KeyboardInterrupt:
            typer.echo("\n👋 Stopped watching")
    else:
        run_once()


if __name__ == "__main__":
    app()