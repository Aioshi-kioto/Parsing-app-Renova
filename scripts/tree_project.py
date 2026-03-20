"""
Генерирует актуальное дерево структуры проекта с размерами (для docs/01-CURRENT-STATE.md).

Исключает: node_modules, .git, __pycache__, venv, .venv, dist, .pytest_cache, *.pyc.
Показывает размер папок в KB, количество файлов. Глубина по умолчанию 4.

Usage:
  python scripts/tree_project.py
  python scripts/tree_project.py --depth 5
  python scripts/tree_project.py --with-files   # перечислить ключевые файлы в ключевых папках
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EXCLUDE_DIRS = {
    "node_modules", ".git", "__pycache__", "venv", ".venv", "dist",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", "coverage_html_report",
    "htmlcov", ".next", ".nuxt", "build", "legacy",
}
# For --compact: also skip these (vendor/submodule or non-app)
EXCLUDE_COMPACT = {"mermaid", ".cursor", "archive"}


def dir_size_kb(path: Path) -> tuple[int, int]:
    """Возвращает (размер в KB, количество файлов)."""
    total = 0
    count = 0
    for f in path.rglob("*"):
        if f.is_file() and not any(ex in f.parts for ex in EXCLUDE_DIRS):
            try:
                total += f.stat().st_size
            except OSError:
                pass
            count += 1
    return total // 1024, count


def format_size(kb: int) -> str:
    if kb >= 1024:
        return f"{kb / 1024:.1f} MB"
    return f"{kb} KB"


def build_tree(
    path: Path,
    prefix: str = "",
    depth: int = 4,
    current: int = 0,
    with_files: bool = False,
    compact: bool = False,
) -> list[str]:
    lines = []
    if current >= depth:
        return lines
    exclude = EXCLUDE_DIRS | (EXCLUDE_COMPACT if compact else set())
    try:
        entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        return lines
    dirs = [e for e in entries if e.is_dir() and e.name not in exclude]
    files = [e for e in entries if e.is_file()]
    all_entries = dirs + files
    for i, entry in enumerate(all_entries):
        is_last = i == len(all_entries) - 1
        connector = "`-- " if is_last else "|-- "
        if entry.is_dir():
            kb, cnt = dir_size_kb(entry)
            size_str = f"  ({format_size(kb)}, {cnt} files)" if kb > 0 or cnt > 0 else ""
            lines.append(f"{prefix}{connector}{entry.name}/{size_str}")
            extension = "    " if is_last else "|   "
            sub = build_tree(entry, prefix + extension, depth, current + 1, with_files, compact)
            lines.extend(sub)
            if with_files and current < 2 and entry.name in ("backend", "frontend", "docs", "test", "scripts"):
                try:
                    subfiles = [f for f in entry.iterdir() if f.is_file() and not f.name.startswith(".")]
                    for sf in sorted(subfiles, key=lambda x: x.name)[:12]:
                        try:
                            sz = sf.stat().st_size // 1024
                            lines.append(f"{prefix}{extension}    {sf.name} ({sz} KB)")
                        except OSError:
                            pass
                except (OSError, PermissionError):
                    pass
        else:
            try:
                sz = entry.stat().st_size // 1024
                sz_str = f" ({sz} KB)" if sz > 0 else ""
                lines.append(f"{prefix}{connector}{entry.name}{sz_str}")
            except OSError:
                lines.append(f"{prefix}{connector}{entry.name}")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description="Project tree with sizes")
    ap.add_argument("--depth", type=int, default=4, help="Max depth (default 4)")
    ap.add_argument("--with-files", action="store_true", help="List key files in key dirs")
    ap.add_argument("--compact", action="store_true", help="Exclude mermaid, .cursor, archive for doc")
    args = ap.parse_args()
    print("# Tree: " + ROOT.name + "/")
    print("# Generated: python scripts/tree_project.py --depth " + str(args.depth) + (" --compact" if args.compact else ""))
    print("")
    lines = build_tree(ROOT, depth=args.depth, with_files=args.with_files, compact=args.compact)
    for line in lines:
        print(line)


if __name__ == "__main__":
    main()
