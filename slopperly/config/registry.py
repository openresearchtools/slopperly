"""Load Slopperly runtime/model/dropdown registry files."""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_yaml(path: str | Path) -> dict:
    """Load a registry YAML file.

    PyYAML is used when present. A tiny fallback supports the subset used by
    Slopperly's checked-in config files so Blender installs without PyYAML can
    still run audits.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    try:
        import yaml
        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        return _load_simple_yaml(text)


def load_models_config(root: str | Path | None = None) -> dict:
    base = Path(root) if root else repo_root()
    return load_yaml(base / "slopperly" / "config" / "models.yaml")


def load_dropdown_profiles(root: str | Path | None = None) -> dict:
    base = Path(root) if root else repo_root()
    return load_yaml(base / "slopperly" / "config" / "dropdown_profiles.yaml")


def load_runtimes_config(root: str | Path | None = None) -> dict:
    base = Path(root) if root else repo_root()
    return load_yaml(base / "slopperly" / "config" / "runtimes.yaml")


def model_entries(root: str | Path | None = None) -> list[dict]:
    data = load_models_config(root)
    entries = data.get("models") if isinstance(data, dict) else None
    return entries if isinstance(entries, list) else []


def _load_simple_yaml(text: str) -> dict:
    """Very small YAML subset parser for mappings/lists/scalars."""
    lines = [
        line.rstrip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    root: dict = {}
    stack: list[tuple[int, object]] = [(-1, root)]

    for raw in lines:
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if line.startswith("- "):
            value = line[2:].strip()
            if not isinstance(parent, list):
                raise ValueError("simple YAML parser expected list parent")
            if ": " in value or value.endswith(":"):
                key, _, val = value.partition(":")
                item: dict = {}
                parent.append(item)
                if val.strip():
                    item[key] = _scalar(val.strip())
                else:
                    child: dict = {}
                    item[key] = child
                    stack.append((indent + 2, child))
                stack.append((indent, item))
            else:
                parent.append(_scalar(value))
            continue

        key, sep, val = line.partition(":")
        if not sep:
            continue
        key = key.strip()
        val = val.strip()
        if isinstance(parent, dict):
            if val:
                parent[key] = _scalar(val)
            else:
                child = [] if _next_is_list(lines, raw) else {}
                parent[key] = child
                stack.append((indent, child))
    return root


def _next_is_list(lines: list[str], current: str) -> bool:
    try:
        idx = lines.index(current)
    except ValueError:
        return False
    cur_indent = len(current) - len(current.lstrip(" "))
    for nxt in lines[idx + 1:]:
        indent = len(nxt) - len(nxt.lstrip(" "))
        if indent <= cur_indent:
            return False
        return nxt.strip().startswith("- ")
    return False


def _scalar(value: str):
    if value in {"null", "None", "~"}:
        return None
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value.strip('"').strip("'")
