from pathlib import Path


def _find_autosmoke_root() -> Path:
    """返回当前工程 AutoSmoke 根目录（兼容不同电脑路径）。"""

    candidate = Path(__file__).resolve()
    if candidate.is_file():
        candidate = candidate.parent

    for parent in [candidate, *candidate.parents]:
        if parent.name.lower() == "autosmoke":
            return parent
    raise RuntimeError("未能定位到 AutoSmoke 根目录")


AUTOSMOKE_ROOT = _find_autosmoke_root()


def as_abs_path(path: str | Path) -> str:
    """把工程内相对路径转为绝对路径；若已是绝对路径则原样返回。"""

    if isinstance(path, Path):
        path = str(path)
    path = path.replace('\\', '/')

    if Path(path).is_absolute():
        return str(Path(path))

    return str((AUTOSMOKE_ROOT / path).resolve())
