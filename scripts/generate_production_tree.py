from __future__ import annotations

import argparse
import os
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
INCLUDED_ROOT_DIRS = ("backend", "frontend", "nginx")
DEFAULT_OUTPUT_FULL = ROOT / "docs" / "production" / "root-structure-tree.md"
DEFAULT_OUTPUT_SIMPLE = ROOT / "docs" / "production" / "root-structure-summary.md"

# Имена сегментов пути: обычно не коммитим / не деплоим как исходники
ARTIFACT_DIR_NAMES = frozenset(
    {
        "__pycache__",
        "node_modules",
        "dist",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".vite",
        "coverage_html_report",
        "htmlcov",
        ".nuxt",
        ".next",
        "build",
    }
)


@dataclass
class TreeStats:
    files: int = 0
    directories: int = 0
    statuses: Counter[str] | None = None

    def __post_init__(self) -> None:
        if self.statuses is None:
            self.statuses = Counter()


@dataclass
class ScopedFile:
    rel: str
    path: Path
    status: str
    mtime: float


def get_git_status_map() -> dict[str, str]:
    """path (posix) -> двухсимвольный код porcelain."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "-uall"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    status_map: dict[str, str] = {}
    for raw_line in result.stdout.splitlines():
        if len(raw_line) < 4:
            continue
        xy = raw_line[:2]
        path_part = raw_line[3:]
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1]
        normalized = path_part.replace("\\", "/")
        status_map[normalized] = xy
    return status_map


def human_size(size_bytes: int) -> str:
    units = ("B", "KB", "MB", "GB")
    size = float(size_bytes)
    unit = units[0]
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            break
        size /= 1024.0
    if unit == "B":
        return f"{int(size)} {unit}"
    return f"{size:.1f} {unit}"


def status_label(rel_posix: str, status_map: dict[str, str]) -> str:
    return status_map.get(rel_posix, "  ")


def collect_scoped_files(status_map: dict[str, str]) -> list[ScopedFile]:
    """Корневые файлы + рекурсивно backend/, frontend/, nginx/."""
    out: list[ScopedFile] = []

    for f in sorted([p for p in ROOT.iterdir() if p.is_file()], key=lambda p: p.name.lower()):
        rel = f.relative_to(ROOT).as_posix()
        try:
            mtime = f.stat().st_mtime
        except OSError:
            mtime = 0.0
        out.append(
            ScopedFile(
                rel=rel,
                path=f,
                status=status_label(rel, status_map),
                mtime=mtime,
            )
        )

    for top in INCLUDED_ROOT_DIRS:
        base = ROOT / top
        if not base.is_dir():
            continue
        # Не заходим в node_modules, dist, __pycache__ и т.д. — не считаем и не читаем файлы там.
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in ARTIFACT_DIR_NAMES]
            for name in filenames:
                if name.endswith(".pyc"):
                    continue
                path = Path(dirpath) / name
                if not path.is_file():
                    continue
                rel = path.relative_to(ROOT).as_posix()
                try:
                    mtime = path.stat().st_mtime
                except OSError:
                    mtime = 0.0
                out.append(
                    ScopedFile(
                        rel=rel,
                        path=path,
                        status=status_label(rel, status_map),
                        mtime=mtime,
                    )
                )
    return out


def _iter_visible_children(path: Path):
    """Дети каталога для полного дерева: без артефактных папок и .pyc."""
    try:
        entries = list(path.iterdir())
    except OSError:
        return
    for child in entries:
        if child.is_dir() and child.name in ARTIFACT_DIR_NAMES:
            continue
        if child.is_file() and child.suffix.lower() == ".pyc":
            continue
        yield child


def add_directory_tree(
    path: Path,
    lines: list[str],
    prefix: str,
    status_map: dict[str, str],
    stats: TreeStats,
) -> None:
    children = sorted(_iter_visible_children(path), key=lambda p: (p.is_file(), p.name.lower()))
    for index, child in enumerate(children):
        is_last = index == len(children) - 1
        connector = "└── " if is_last else "├── "
        branch = "    " if is_last else "│   "
        rel = child.relative_to(ROOT).as_posix()

        if child.is_dir():
            stats.directories += 1
            lines.append(f"{prefix}{connector}[DIR] {rel}/")
            add_directory_tree(child, lines, prefix + branch, status_map, stats)
            continue

        stats.files += 1
        code = status_label(rel, status_map)
        stats.statuses[code] += 1
        size = human_size(child.stat().st_size)
        mtime = datetime.fromtimestamp(child.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        lines.append(f"{prefix}{connector}[{code}] {rel} ({size}, {mtime})")


def build_tree(status_map: dict[str, str]) -> tuple[list[str], TreeStats]:
    lines: list[str] = []
    stats = TreeStats()

    root_files = sorted([p for p in ROOT.iterdir() if p.is_file()], key=lambda p: p.name.lower())
    included_dirs = [ROOT / name for name in INCLUDED_ROOT_DIRS if (ROOT / name).exists()]

    lines.append(f"{ROOT.name}/")

    for file_path in root_files:
        code = status_label(file_path.relative_to(ROOT).as_posix(), status_map)
        stats.files += 1
        stats.statuses[code] += 1
        size = human_size(file_path.stat().st_size)
        mtime = datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        rel = file_path.relative_to(ROOT).as_posix()
        lines.append(f"├── [{code}] {rel} ({size}, {mtime})")

    for index, directory in enumerate(included_dirs):
        is_last = index == len(included_dirs) - 1
        connector = "└── " if is_last else "├── "
        prefix = "    " if is_last else "│   "
        stats.directories += 1
        rel = directory.relative_to(ROOT).as_posix()
        lines.append(f"{connector}[DIR] {rel}/")
        add_directory_tree(directory, lines, prefix, status_map, stats)

    return lines, stats


def render_markdown_full(tree_lines: list[str], stats: TreeStats) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    non_clean = {k: v for k, v in stats.statuses.items() if k != "  "}
    status_lines = [f"- `{k}`: {v}" for k, v in sorted(non_clean.items())]
    if not status_lines:
        status_lines.append("- Нет измененных/новых файлов в выбранном срезе.")

    return "\n".join(
        [
            "# Production: полное дерево (детально)",
            "",
            "> Для быстрого разбора используй `root-structure-summary.md` или `python scripts/generate_production_tree.py --simple`.",
            "",
            f"- Generated at: `{generated_at}`",
            "- Scope: root files + `backend/` + `frontend/` + `nginx/`",
            "- Исключено из дерева (не обходится): `__pycache__`, `node_modules`, `dist`, кэши сборки (см. `ARTIFACT_DIR_NAMES` в скрипте).",
            f"- Total files: `{stats.files}`",
            f"- Total directories: `{stats.directories}`",
            "",
            "## Git Status Summary (selected scope)",
            *status_lines,
            "",
            "## Tree",
            "",
            "```text",
            *tree_lines,
            "```",
            "",
            "## Легенда статусов",
            "- `[  ]` чисто",
            "- `[??]` не отслеживается",
            "- `[ M]` изменён в рабочей копии",
            "- `[M ]` в индексе (staged)",
            "- Остальные коды — как в `git status --porcelain`.",
            "",
        ]
    )


def build_shallow_tree_lines(max_depth: int = 2) -> list[str]:
    """Только каталоги до max_depth от backend|frontend|nginx; без файлов."""
    lines: list[str] = []
    for top in INCLUDED_ROOT_DIRS:
        base = ROOT / top
        if not base.is_dir():
            continue
        lines.append(f"{top}/")
        try:
            children = sorted(
                (c for c in base.iterdir() if not (c.is_dir() and c.name in ARTIFACT_DIR_NAMES)),
                key=lambda p: p.name.lower(),
            )
        except OSError:
            continue
        for i, child in enumerate(children):
            is_last = i == len(children) - 1
            conn = "└── " if is_last else "├── "
            br = "    " if is_last else "│   "
            if child.is_dir():
                lines.append(f"{conn}[DIR] {child.name}/")
                if max_depth >= 2:
                    try:
                        sub = sorted(
                            (
                                c
                                for c in child.iterdir()
                                if not (c.is_dir() and c.name in ARTIFACT_DIR_NAMES)
                            ),
                            key=lambda p: p.name.lower(),
                        )
                    except OSError:
                        continue
                    for j, subc in enumerate(sub):
                        sub_last = j == len(sub) - 1
                        sub_conn = "└── " if sub_last else "├── "
                        if subc.is_dir():
                            lines.append(f"{br}{sub_conn}[DIR] {child.name}/{subc.name}/")
                        else:
                            lines.append(f"{br}{sub_conn}{subc.name}")
            else:
                lines.append(f"{conn}{child.name}")
    return lines


def render_markdown_simple(files: list[ScopedFile]) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meaningful = files

    def count_status(items: list[ScopedFile], code: str) -> int:
        return sum(1 for x in items if x.status == code)

    status_counts = Counter(f.status for f in meaningful)
    non_clean = {k: v for k, v in status_counts.items() if k != "  "}
    status_summary = [f"- `{k}`: {v}" for k, v in sorted(non_clean.items())]
    if not status_summary:
        status_summary.append("- Нет изменений среди отсканированных файлов.")

    untracked_paths = sorted(sf.rel for sf in meaningful if sf.status == "??")

    changed_meaningful = sorted(
        (sf for sf in meaningful if sf.status not in ("  ", "??")),
        key=lambda x: x.rel,
    )

    oldest_meaningful = sorted(meaningful, key=lambda x: x.mtime)[:25]
    oldest_lines = []
    for sf in oldest_meaningful:
        dt = datetime.fromtimestamp(sf.mtime).strftime("%Y-%m-%d")
        oldest_lines.append(f"- `{dt}` · `[{sf.status}]` · `{sf.rel}`")

    shallow = build_shallow_tree_lines(max_depth=2)

    lines_out = [
        "# Production: краткий срез (для решений что удалить / оставить)",
        "",
        f"- Сгенерировано: `{generated_at}`",
        "- Область: **только** корневые файлы + `backend/` + `frontend/` + `nginx/`",
        "- **Не обходятся** (рекурсивно, файлы изнутри не попадают в отчёт): "
        + ", ".join(f"`{n}`" for n in sorted(ARTIFACT_DIR_NAMES))
        + ".",
        "",
        "## Сводка",
        f"- Файлов в отчёте: **{len(meaningful)}**",
        f"- Чистых в git: **{count_status(meaningful, '  ')}**",
        "",
        "## Статусы git (отсканированные файлы)",
        *status_summary,
        "",
        "### Не отслеживаются `??` — решить: в репозиторий или в `.gitignore`",
    ]
    if untracked_paths:
        lines_out.extend(f"- `{p}`" for p in untracked_paths)
    else:
        lines_out.append("- (нет)")

    lines_out.extend(
        [
            "",
            "### Изменено / в индексе / переименовано и т.д. (не `??`, не чисто)",
        ]
    )
    if changed_meaningful:
        for sf in changed_meaningful:
            lines_out.append(f"- `[{sf.status}]` `{sf.rel}`")
    else:
        lines_out.append("- (нет)")

    lines_out.extend(
        [
            "",
            "## Исключённые каталоги",
            "Они **не сканируются** (ни подсчёт, ни git-списки оттуда). На сервер обычно не кладут как исходники; локально держите в `.gitignore` и/или пересобирайте (`npm ci`, `npm run build` и т.д.).",
        ]
    )
    lines_out.extend(f"- `{n}`" for n in sorted(ARTIFACT_DIR_NAMES))

    lines_out.extend(
        [
            "",
            "## Давно не трогались (25 самых старых по mtime среди значимых)",
            "*Не значит «удалить», но кандидаты на ревизию или мёртвый код.*",
            *oldest_lines,
            "",
            "## Каркас каталогов (глубина 2, без простыни файлов)",
            "",
            "```text",
            *shallow,
            "```",
            "",
            "## Полное дерево",
            "Если нужна простыня по каждому файлу: `python scripts/generate_production_tree.py --full` → `docs/production/root-structure-tree.md`.",
            "",
        ]
    )
    return "\n".join(lines_out)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Отчёты по структуре для продакшена: краткий (--simple) или полное дерево (--full)."
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Только краткий отчёт (по умолчанию)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Полное рекурсивное дерево со всеми файлами",
    )
    parser.add_argument(
        "--output-simple",
        default=str(DEFAULT_OUTPUT_SIMPLE),
        help="Путь для краткого отчёта",
    )
    parser.add_argument(
        "--output-full",
        default=str(DEFAULT_OUTPUT_FULL),
        help="Путь для полного дерева",
    )
    args = parser.parse_args()

    do_full = args.full
    do_simple = args.simple or not do_full

    status_map = get_git_status_map()

    if do_simple:
        out_simple = Path(args.output_simple)
        out_simple.parent.mkdir(parents=True, exist_ok=True)
        scoped = collect_scoped_files(status_map)
        out_simple.write_text(render_markdown_simple(scoped), encoding="utf-8")
        print(f"Saved (simple): {out_simple}")

    if do_full:
        out_full = Path(args.output_full)
        out_full.parent.mkdir(parents=True, exist_ok=True)
        tree_lines, stats = build_tree(status_map)
        out_full.write_text(render_markdown_full(tree_lines, stats), encoding="utf-8")
        print(f"Saved (full): {out_full}")


if __name__ == "__main__":
    main()
