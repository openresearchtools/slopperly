"""Download/cache local model artifacts declared in Slopperly's registry."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from slopperly.config.registry import model_entries


GENERIC_FILE_MARKERS = (
    "model artifacts",
    "configured by",
    "downloaded by",
)


@dataclass
class DownloadResult:
    status: str
    model: str
    detail: str
    path: str = ""


def huggingface_repo_id(model_source: str) -> str | None:
    parsed = urlparse(str(model_source))
    if parsed.netloc.lower() not in {"huggingface.co", "www.huggingface.co"}:
        return None
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        return None
    return "/".join(parts[:2])


def is_exact_file(value: str) -> bool:
    text = str(value).strip()
    if not text:
        return False
    lowered = text.lower()
    if any(marker in lowered for marker in GENERIC_FILE_MARKERS):
        return False
    return "/" not in text and "\\" not in text


def target_path(cache_root: Path, entry: dict, filename: str) -> Path:
    local_cache = Path(str(entry.get("local_cache_path") or entry.get("logical_name")))
    base = cache_root / local_cache
    if base.name == filename:
        return base
    return base / filename


def selected_entries(root: Path, names: list[str] | None = None) -> list[dict]:
    entries = model_entries(root)
    if not names:
        return entries
    wanted = set(names)
    return [entry for entry in entries if entry.get("logical_name") in wanted]


def download_models(
    *,
    root: Path,
    profile: str,
    cache_root: Path,
    names: list[str] | None = None,
    accept_licenses: bool = False,
    dry_run: bool = False,
) -> list[DownloadResult]:
    results: list[DownloadResult] = []
    entries = selected_entries(root, names)
    seen = {entry.get("logical_name") for entry in entries}
    for missing in sorted(set(names or []) - seen):
        results.append(DownloadResult("BLOCKED", missing, "model not found in slopperly/config/models.yaml"))

    for entry in entries:
        name = entry.get("logical_name", "<unnamed>")
        source = str(entry.get("model_source") or "")
        repo_id = huggingface_repo_id(source)
        required_files = entry.get("required_files") or []
        if not isinstance(required_files, list) or not required_files:
            results.append(DownloadResult("BLOCKED", name, "required_files is empty or invalid"))
            continue
        if not repo_id:
            results.append(
                DownloadResult(
                    "BLOCKED",
                    name,
                    f"model_source is not a Hugging Face artifact URL: {source!r}",
                )
            )
            continue

        for raw_file in required_files:
            filename = str(raw_file).strip()
            dest = target_path(cache_root, entry, filename)
            if not is_exact_file(filename):
                results.append(
                    DownloadResult(
                        "BLOCKED",
                        name,
                        f"required file is not exact: {filename!r}",
                        str(dest),
                    )
                )
                continue
            if dest.is_file() and dest.stat().st_size > 0:
                results.append(DownloadResult("PASS", name, "artifact already cached", str(dest)))
                continue
            if dry_run:
                results.append(
                    DownloadResult(
                        "PLAN",
                        name,
                        f"would download {repo_id}/{filename} for profile {profile}",
                        str(dest),
                    )
                )
                continue
            if not accept_licenses:
                results.append(
                    DownloadResult(
                        "BLOCKED",
                        name,
                        "download requires --accept-licenses",
                        str(dest),
                    )
                )
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                from huggingface_hub import hf_hub_download
            except Exception as exc:
                results.append(
                    DownloadResult(
                        "BLOCKED",
                        name,
                        f"huggingface_hub is required for downloads: {exc}",
                        str(dest),
                    )
                )
                continue
            try:
                downloaded = hf_hub_download(
                    repo_id=repo_id,
                    filename=filename,
                    local_dir=str(dest.parent),
                    local_dir_use_symlinks=False,
                )
            except Exception as exc:
                results.append(
                    DownloadResult(
                        "BLOCKED",
                        name,
                        f"download failed for {repo_id}/{filename}: {exc}",
                        str(dest),
                    )
                )
                continue
            final_path = Path(downloaded)
            if final_path != dest and final_path.is_file() and not dest.exists():
                final_path.replace(dest)
            results.append(DownloadResult("PASS", name, "artifact downloaded", str(dest)))
    return results


def print_results(results: list[DownloadResult]) -> None:
    for result in results:
        suffix = f" -> {result.path}" if result.path else ""
        print(f"{result.status} {result.model}: {result.detail}{suffix}")
    counts = {status: sum(1 for r in results if r.status == status) for status in {"PASS", "PLAN", "BLOCKED"}}
    print(
        "Model artifact records: "
        f"{counts['PASS']} cached/downloaded, {counts['PLAN']} planned, {counts['BLOCKED']} blocked."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download local model artifacts declared by Slopperly")
    parser.add_argument("--root", default=".")
    parser.add_argument("--profile", default="smoke_16gb")
    parser.add_argument("--cache-root", default=".slopperly/model-cache")
    parser.add_argument("--model", action="append", dest="models", help="logical model name; may be repeated")
    parser.add_argument("--accept-licenses", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    cache_root = (root / args.cache_root).resolve()
    results = download_models(
        root=root,
        profile=args.profile,
        cache_root=cache_root,
        names=args.models,
        accept_licenses=args.accept_licenses,
        dry_run=args.dry_run,
    )
    print_results(results)
    blocked = any(result.status == "BLOCKED" for result in results)
    return 0 if args.report_only or not blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
