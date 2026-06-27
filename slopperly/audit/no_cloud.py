"""Static no-cloud audit for production Slopperly paths."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

PATTERNS = [
    "queue.fal.run",
    "fal.ai",
    "FAL_KEY",
    "google.genai",
    "GEMINI_API_KEY",
    "MiniMax_API.txt",
    "api.minimaxi.chat",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "ELEVENLABS_API_KEY",
    "REPLICATE_API_TOKEN",
    "api.stability.ai",
    "runway",
    "vertex",
    "bedrock",
]

ALLOWLIST_PREFIXES = (
    "AGENTS.md",
    ".claude/",
    "README.md",
    "docs/",
    "reference/",
    "remote_backends/README.md",
    "remote_backends/requirements.txt",
    "slopperly/audit/no_cloud.py",
    "unsupported_models_plugins/",
)


def iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith(ALLOWLIST_PREFIXES):
            continue
        yield path, rel


def scan(root: Path) -> list[tuple[str, int, str, str]]:
    hits = []
    compiled = [(p, re.compile(re.escape(p), re.IGNORECASE)) for p in PATTERNS]
    for path, rel in iter_files(root):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(lines, 1):
            for pattern, regex in compiled:
                if regex.search(line):
                    hits.append((rel, lineno, pattern, line.strip()[:180]))
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail if production code references cloud inference providers")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    hits = scan(root)
    if hits:
        for rel, lineno, pattern, line in hits:
            print(f"{rel}:{lineno}: {pattern}: {line}")
        return 1
    print("No production cloud inference references found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
