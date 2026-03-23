import os
import argparse
import time
import pathspec
from colorama import Fore, Style, init

# IMPORTANT: convert=True fixes Windows color issues
init(autoreset=True, convert=True)

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


def load_gitignore(root):
    path = os.path.join(root, ".gitignore")
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return pathspec.PathSpec.from_lines("gitwildmatch", f.read().splitlines())


def format_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def get_icon(name, is_dir):
    if is_dir:
        return ICONS["folder"]
    return ICONS.get(os.path.splitext(name)[1], ICONS["file"])


def color_name(name, is_dir):
    if is_dir:
        return Fore.BLUE + name + Style.RESET_ALL

    ext = os.path.splitext(name)[1]

    if ext == ".py":
        return Fore.GREEN + name + Style.RESET_ALL
    if ext in [".js", ".ts"]:
        return Fore.YELLOW + name + Style.RESET_ALL
    if ext == ".json":
        return Fore.CYAN + name + Style.RESET_ALL
    if ext == ".md":
        return Fore.MAGENTA + name + Style.RESET_ALL

    return name


def should_ignore(item, rel_path, spec, extra):
    if item in DEFAULT_IGNORES or item in extra:
        return True
    if spec and spec.match_file(rel_path):
        return True
    return False


def generate_tree(path, root, spec, prefix, output, depth, max_depth, args, extra):
    if max_depth is not None and depth > max_depth:
        return

    try:
        items = sorted(os.listdir(path))
    except:
        return

    filtered = []
    for item in items:
        full = os.path.join(path, item)
        rel = os.path.relpath(full, root)

        if should_ignore(item, rel, spec, extra):
            continue

        filtered.append(item)

    if not filtered:
        return

    pointers = ["├── "] * (len(filtered) - 1) + ["└── "]

    for pointer, item in zip(pointers, filtered):
        full = os.path.join(path, item)
        is_dir = os.path.isdir(full)

        # --- Build display properly ---
        icon = get_icon(item, is_dir) if args.icons else ""
        name = item

        # apply color ONLY to name
        if args.color:
            name = color_name(name, is_dir)

        # size
        if args.size and not is_dir:
            try:
                size = os.path.getsize(full)
                name += f" ({format_size(size)})"
            except:
                pass

        display = f"{icon} {name}" if icon else name

        line = prefix + pointer + display
        output.append(line)

        if is_dir:
            ext = "│   " if pointer == "├── " else "    "
            generate_tree(full, root, spec, prefix + ext, output,
                          depth + 1, max_depth, args, extra)


# -------- TUI --------
def run_tui(root, spec, extra):
    from rich.tree import Tree
    from rich import print as rprint

    def build(path, tree):
        try:
            items = sorted(os.listdir(path))
        except:
            return

        for item in items:
            full = os.path.join(path, item)
            rel = os.path.relpath(full, root)

            if should_ignore(item, rel, spec, extra):
                continue

            branch = tree.add(f"[bold blue]{item}[/]" if os.path.isdir(full) else item)

            if os.path.isdir(full):
                build(full, branch)

    tree = Tree(f"[bold green]{os.path.basename(root)}[/]")
    build(root, tree)
    rprint(tree)


def run_once(args):
    root = os.path.abspath(args.path)

    if not os.path.exists(root):
        print("❌ Path does not exist")
        return

    spec = load_gitignore(root)
    extra = set(args.ignore)

    if args.tui:
        run_tui(root, spec, extra)
        return

    output = []
    header = root if args.fullpath else os.path.basename(root)
    output.append(header)

    generate_tree(root, root, spec, "", output, 1, args.depth, args, extra)

    if args.markdown:
        output = ["```"] + output + ["```"]

    print("\n".join(output))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write("\n".join(output))
        print(f"\n✅ Saved to {args.output}")


def main():
    parser = argparse.ArgumentParser(description="🔥 gettree - ultimate folder tree CLI")

    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--ignore", nargs="*", default=[])
    parser.add_argument("--output")
    parser.add_argument("--fullpath", action="store_true")

    parser.add_argument("--depth", type=int)
    parser.add_argument("--size", action="store_true")
    parser.add_argument("--icons", action="store_true")
    parser.add_argument("--color", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--tui", action="store_true")

    args = parser.parse_args()

    if args.watch:
        try:
            while True:
                os.system("cls" if os.name == "nt" else "clear")
                run_once(args)
                time.sleep(2)
        except KeyboardInterrupt:
            print("\n👋 Stopped watching")
    else:
        run_once(args)


if __name__ == "__main__":
    main()