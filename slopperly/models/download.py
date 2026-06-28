"""Download/cache local model artifacts declared in Slopperly's registry."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from slopperly.config.registry import model_entries


GENERIC_FILE_MARKERS = (
    "model artifacts",
    "configured by",
    "downloaded by",
)
MOSS_TTS_NANO_LOGICAL_NAME = "moss_tts_nano_vllm_omni"
MOSS_AUDIO_TOKENIZER_AUX_ID = "moss_audio_tokenizer_nano"
MOSS_AUDIO_TOKENIZER_CONFIG_KEY = "audio_tokenizer_pretrained_name_or_path"


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


def is_safe_relative_file(value: str) -> bool:
    text = str(value).strip()
    if not text:
        return False
    lowered = text.lower()
    if any(marker in lowered for marker in GENERIC_FILE_MARKERS):
        return False
    path = Path(text)
    if path.is_absolute() or ".." in path.parts:
        return False
    return True


def hf_file_source_and_target(value) -> tuple[str, str] | None:
    if isinstance(value, str):
        filename = value.strip()
        return (filename, filename) if filename else None
    if not isinstance(value, dict):
        return None
    source = str(value.get("path") or value.get("source") or "").strip()
    target = str(value.get("target") or Path(source).name).strip()
    if not source or not target:
        return None
    return source, target


def target_path(cache_root: Path, entry: dict, filename: str) -> Path:
    local_cache = Path(str(entry.get("local_cache_path") or entry.get("logical_name")))
    base = cache_root / local_cache
    if base.name == filename:
        return base
    return base / filename


def snapshot_path(cache_root: Path, entry: dict) -> Path:
    return cache_root / Path(str(entry.get("local_cache_path") or entry.get("logical_name")))


def torchaudio_asset_key(entry: dict) -> str:
    params = entry.get("default_parameters") or {}
    if not isinstance(params, dict):
        return ""
    key = str(params.get("torchaudio_asset_key") or "").strip()
    return key if is_safe_relative_file(key) else ""


def torch_hub_dir() -> Path:
    try:
        import torch

        return Path(torch.hub.get_dir())
    except Exception:
        torch_home = Path(os.environ.get("TORCH_HOME", Path.home() / ".cache" / "torch"))
        return torch_home / "hub"


def torchaudio_cache_path(asset_key: str) -> Path:
    return torch_hub_dir() / "torchaudio" / Path(asset_key)


def mirror_torchaudio_asset(
    *,
    entry: dict,
    name: str,
    source_path: Path,
    dry_run: bool,
) -> DownloadResult | None:
    asset_key = torchaudio_asset_key(entry)
    if not asset_key:
        return None
    dest = torchaudio_cache_path(asset_key)
    if dry_run:
        return DownloadResult(
            "PLAN",
            name,
            f"would mirror Torchaudio asset key {asset_key}",
            str(dest),
        )
    if not source_path.is_file() or source_path.stat().st_size <= 0:
        return DownloadResult(
            "BLOCKED",
            name,
            f"Torchaudio source artifact is missing: {source_path}",
            str(dest),
        )
    if dest.is_file() and dest.stat().st_size == source_path.stat().st_size:
        return DownloadResult("PASS", name, "Torchaudio asset already mirrored", str(dest))
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, dest)
    return DownloadResult("PASS", name, "Torchaudio asset mirrored", str(dest))


def selected_entries(root: Path, names: list[str] | None = None) -> list[dict]:
    entries = model_entries(root)
    if not names:
        return entries
    wanted = set(names)
    return [entry for entry in entries if entry.get("logical_name") in wanted]


def auxiliary_entries(entry: dict) -> list[dict]:
    sources = entry.get("auxiliary_sources") or []
    return sources if isinstance(sources, list) else []


def artifact_entry_name(parent_name: str, entry: dict) -> str:
    artifact_id = str(entry.get("id") or entry.get("logical_name") or "auxiliary")
    return artifact_id if artifact_id == parent_name else f"{parent_name}:{artifact_id}"


def moss_audio_tokenizer_entry(entry: dict) -> dict | None:
    for auxiliary in auxiliary_entries(entry):
        if str(auxiliary.get("id") or "") == MOSS_AUDIO_TOKENIZER_AUX_ID:
            return auxiliary
    return None


def rewrite_moss_tts_nano_config(
    *,
    entry: dict,
    name: str,
    cache_root: Path,
    dry_run: bool,
) -> DownloadResult | None:
    if str(entry.get("logical_name") or "") != MOSS_TTS_NANO_LOGICAL_NAME:
        return None
    tokenizer_entry = moss_audio_tokenizer_entry(entry)
    if tokenizer_entry is None:
        return DownloadResult("BLOCKED", name, "MOSS audio tokenizer auxiliary source is missing")

    model_config = snapshot_path(cache_root, entry) / "config.json"
    tokenizer_dir = snapshot_path(cache_root, tokenizer_entry)
    if dry_run:
        return DownloadResult(
            "PLAN",
            f"{name}:moss_local_tokenizer_config",
            f"would point MOSS config at local audio tokenizer {tokenizer_dir}",
            str(model_config),
        )
    if not model_config.is_file():
        return DownloadResult("BLOCKED", name, f"MOSS config is missing: {model_config}", str(model_config))
    if not (tokenizer_dir / "config.json").is_file():
        return DownloadResult(
            "BLOCKED",
            name,
            f"MOSS audio tokenizer snapshot is missing: {tokenizer_dir}",
            str(tokenizer_dir),
        )

    data = json.loads(model_config.read_text(encoding="utf-8"))
    desired = str(tokenizer_dir.resolve())
    if data.get(MOSS_AUDIO_TOKENIZER_CONFIG_KEY) == desired:
        return DownloadResult("PASS", name, "MOSS config already points at local audio tokenizer", str(model_config))
    data[MOSS_AUDIO_TOKENIZER_CONFIG_KEY] = desired
    model_config.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return DownloadResult("PASS", name, "MOSS config updated to local audio tokenizer", str(model_config))


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
        results.extend(
            download_artifact_entry(
                entry=entry,
                name=name,
                cache_root=cache_root,
                profile=profile,
                accept_licenses=accept_licenses,
                dry_run=dry_run,
            )
        )
        for auxiliary in auxiliary_entries(entry):
            results.extend(
                download_artifact_entry(
                    entry=auxiliary,
                    name=artifact_entry_name(str(name), auxiliary),
                    cache_root=cache_root,
                    profile=profile,
                    accept_licenses=accept_licenses,
                    dry_run=dry_run,
                )
            )
        postprocess = rewrite_moss_tts_nano_config(
            entry=entry,
            name=str(name),
            cache_root=cache_root,
            dry_run=dry_run,
        )
        if postprocess:
            results.append(postprocess)
    return results


def download_artifact_entry(
    *,
    entry: dict,
    name: str,
    cache_root: Path,
    profile: str,
    accept_licenses: bool,
    dry_run: bool,
) -> list[DownloadResult]:
    source = str(entry.get("model_source") or "")
    repo_id = huggingface_repo_id(source)
    download_mode = str(entry.get("download_mode") or "hf_file")
    required_files = entry.get("required_files") or []
    if not isinstance(required_files, list) or not required_files:
        return [DownloadResult("BLOCKED", name, "required_files is empty or invalid")]
    if not repo_id:
        return [
            DownloadResult(
                "BLOCKED",
                name,
                f"model_source is not a Hugging Face artifact URL: {source!r}",
            )
        ]

    if download_mode == "hf_snapshot":
        return download_snapshot(
            entry=entry,
            name=name,
            repo_id=repo_id,
            required_files=required_files,
            cache_root=cache_root,
            profile=profile,
            accept_licenses=accept_licenses,
            dry_run=dry_run,
        )
    if download_mode != "hf_file":
        return [
            DownloadResult(
                "BLOCKED",
                name,
                f"unsupported download_mode {download_mode!r}",
            )
        ]

    results: list[DownloadResult] = []
    for raw_file in required_files:
        file_spec = hf_file_source_and_target(raw_file)
        if file_spec is None:
            results.append(
                DownloadResult(
                    "BLOCKED",
                    name,
                    f"required file is not exact: {raw_file!r}",
                )
            )
            continue
        source_file, filename = file_spec
        dest = target_path(cache_root, entry, filename)
        if not is_safe_relative_file(source_file) or not is_exact_file(filename):
            results.append(
                DownloadResult(
                    "BLOCKED",
                    name,
                    f"required file is not exact: {raw_file!r}",
                    str(dest),
                )
            )
            continue
        if dest.is_file() and dest.stat().st_size > 0:
            results.append(DownloadResult("PASS", name, "artifact already cached", str(dest)))
            mirror = mirror_torchaudio_asset(
                entry=entry,
                name=name,
                source_path=dest,
                dry_run=False,
            )
            if mirror:
                results.append(mirror)
            continue
        if dry_run:
            results.append(
                DownloadResult(
                    "PLAN",
                    name,
                    f"would download {repo_id}/{source_file} for profile {profile}",
                    str(dest),
                )
            )
            mirror = mirror_torchaudio_asset(
                entry=entry,
                name=name,
                source_path=dest,
                dry_run=True,
            )
            if mirror:
                results.append(mirror)
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
                filename=source_file,
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
        mirror = mirror_torchaudio_asset(
            entry=entry,
            name=name,
            source_path=dest,
            dry_run=False,
        )
        if mirror:
            results.append(mirror)
    return results


def download_snapshot(
    *,
    entry: dict,
    name: str,
    repo_id: str,
    required_files: list,
    cache_root: Path,
    profile: str,
    accept_licenses: bool,
    dry_run: bool,
) -> list[DownloadResult]:
    results: list[DownloadResult] = []
    dest = snapshot_path(cache_root, entry)
    invalid = [str(filename) for filename in required_files if not is_safe_relative_file(str(filename))]
    if invalid:
        return [
            DownloadResult(
                "BLOCKED",
                name,
                f"snapshot required_files contain unsafe or generic entries: {invalid!r}",
                str(dest),
            )
        ]
    missing = [
        str(filename)
        for filename in required_files
        if not (dest / str(filename)).is_file() or (dest / str(filename)).stat().st_size <= 0
    ]
    if not missing:
        return [DownloadResult("PASS", name, "snapshot already cached", str(dest))]
    if dry_run:
        return [
            DownloadResult(
                "PLAN",
                name,
                f"would snapshot_download {repo_id} for profile {profile}; missing evidence files: {missing}",
                str(dest),
            )
        ]
    if not accept_licenses:
        return [
            DownloadResult(
                "BLOCKED",
                name,
                "snapshot download requires --accept-licenses",
                str(dest),
            )
        ]
    try:
        from huggingface_hub import snapshot_download
    except Exception as exc:
        return [
            DownloadResult(
                "BLOCKED",
                name,
                f"huggingface_hub is required for snapshot downloads: {exc}",
                str(dest),
            )
        ]
    try:
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(dest),
            local_dir_use_symlinks=False,
            allow_patterns=entry.get("allow_patterns"),
            ignore_patterns=entry.get("ignore_patterns"),
        )
    except Exception as exc:
        return [
            DownloadResult(
                "BLOCKED",
                name,
                f"snapshot download failed for {repo_id}: {exc}",
                str(dest),
            )
        ]
    remaining = [
        str(filename)
        for filename in required_files
        if not (dest / str(filename)).is_file() or (dest / str(filename)).stat().st_size <= 0
    ]
    if remaining:
        return [
            DownloadResult(
                "BLOCKED",
                name,
                f"snapshot downloaded but required evidence files are missing: {remaining}",
                str(dest),
            )
        ]
    results.append(DownloadResult("PASS", name, "snapshot downloaded", str(dest)))
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
        dry_run=args.dry_run or args.report_only,
    )
    print_results(results)
    blocked = any(result.status == "BLOCKED" for result in results)
    return 0 if args.report_only or not blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
