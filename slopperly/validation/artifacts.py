"""Real artifact validators used by Slopperly runtime and GPU tests."""

from __future__ import annotations

import json
import math
import os
import struct
import subprocess
import wave
from pathlib import Path


class ArtifactValidationError(AssertionError):
    """Raised when a generated artifact does not satisfy its contract."""


def validate_image(
    path: str,
    *,
    expected_width: int | None = None,
    expected_height: int | None = None,
    require_alpha: bool = False,
) -> dict:
    file_path = _require_file(path)
    info = _image_info(file_path)
    if expected_width is not None and info["width"] != expected_width:
        raise ArtifactValidationError(f"image width {info['width']} != {expected_width}")
    if expected_height is not None and info["height"] != expected_height:
        raise ArtifactValidationError(f"image height {info['height']} != {expected_height}")
    if require_alpha and not info.get("alpha"):
        raise ArtifactValidationError("image does not contain an alpha channel")
    return info


def validate_audio(
    path: str,
    *,
    expected_duration: float | None = None,
    duration_tolerance: float = 0.25,
    expected_sample_rate: int | None = None,
    require_non_silent: bool = True,
) -> dict:
    file_path = _require_file(path)
    if file_path.suffix.lower() == ".wav":
        info = _wav_info(file_path)
    else:
        info = _ffprobe_audio_info(file_path)
    if expected_duration is not None and not _close(
        info["duration"], expected_duration, duration_tolerance
    ):
        raise ArtifactValidationError(
            f"audio duration {info['duration']:.3f}s not within "
            f"{duration_tolerance:.3f}s of {expected_duration:.3f}s"
        )
    if expected_sample_rate is not None and info["sample_rate"] != expected_sample_rate:
        raise ArtifactValidationError(
            f"audio sample_rate {info['sample_rate']} != {expected_sample_rate}"
        )
    if require_non_silent and info.get("rms", 0.0) <= 0.0:
        raise ArtifactValidationError("audio waveform is silent")
    return info


def validate_video(
    path: str,
    *,
    expected_width: int | None = None,
    expected_height: int | None = None,
    expected_fps: float | None = None,
    expected_duration: float | None = None,
    duration_tolerance: float = 0.05,
    require_audio: bool = False,
) -> dict:
    file_path = _require_file(path)
    info = _ffprobe_video_info(file_path)
    if expected_width is not None and info.get("width") != expected_width:
        raise ArtifactValidationError(f"video width {info.get('width')} != {expected_width}")
    if expected_height is not None and info.get("height") != expected_height:
        raise ArtifactValidationError(f"video height {info.get('height')} != {expected_height}")
    if expected_fps is not None and not _close(info.get("fps", 0.0), expected_fps, 0.01):
        raise ArtifactValidationError(f"video fps {info.get('fps')} != {expected_fps}")
    if expected_duration is not None and not _close(
        info.get("duration", 0.0), expected_duration, duration_tolerance
    ):
        raise ArtifactValidationError(
            f"video duration {info.get('duration'):.3f}s not within "
            f"{duration_tolerance:.3f}s of {expected_duration:.3f}s"
        )
    if require_audio and not info.get("has_audio"):
        raise ArtifactValidationError("video has no audio stream")
    return info


def validate_text(
    text_or_path: str,
    *,
    max_chars: int | None = None,
    forbidden_fragments: list[str] | None = None,
) -> dict:
    text = Path(text_or_path).read_text(encoding="utf-8") if os.path.isfile(text_or_path) else text_or_path
    if not text.strip():
        raise ArtifactValidationError("text output is empty")
    if max_chars is not None and len(text) > max_chars:
        raise ArtifactValidationError(f"text length {len(text)} > {max_chars}")
    for fragment in forbidden_fragments or []:
        if fragment.lower() in text.lower():
            raise ArtifactValidationError(f"text contains forbidden fragment {fragment!r}")
    return {"kind": "text", "chars": len(text)}


def _require_file(path: str) -> Path:
    file_path = Path(path)
    if not file_path.is_file():
        raise ArtifactValidationError(f"artifact does not exist: {path}")
    if file_path.stat().st_size <= 0:
        raise ArtifactValidationError(f"artifact is empty: {path}")
    return file_path


def _image_info(path: Path) -> dict:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        width, height = struct.unpack(">II", data[16:24])
        color_type = data[25]
        return {
            "kind": "image",
            "format": "PNG",
            "width": width,
            "height": height,
            "alpha": color_type in {4, 6},
        }
    if data.startswith(b"\xff\xd8"):
        return _jpeg_info(data)
    try:
        from PIL import Image
        with Image.open(path) as img:
            return {
                "kind": "image",
                "format": img.format or path.suffix.upper().lstrip("."),
                "width": img.width,
                "height": img.height,
                "alpha": "A" in img.getbands(),
            }
    except Exception as exc:
        raise ArtifactValidationError(f"unsupported or unreadable image: {path}") from exc


def _jpeg_info(data: bytes) -> dict:
    idx = 2
    while idx < len(data):
        if data[idx] != 0xFF:
            idx += 1
            continue
        marker = data[idx + 1]
        idx += 2
        if marker in {0xD8, 0xD9}:
            continue
        length = struct.unpack(">H", data[idx:idx + 2])[0]
        if marker in set(range(0xC0, 0xC4)) | set(range(0xC5, 0xC8)) | set(range(0xC9, 0xCC)) | set(range(0xCD, 0xD0)):
            height, width = struct.unpack(">HH", data[idx + 3:idx + 7])
            return {"kind": "image", "format": "JPEG", "width": width, "height": height, "alpha": False}
        idx += length
    raise ArtifactValidationError("JPEG dimensions not found")


def _wav_info(path: Path) -> dict:
    with wave.open(str(path), "rb") as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        raw = wav.readframes(frames)
    duration = frames / float(rate or 1)
    rms = _pcm_rms(raw, width)
    return {
        "kind": "audio",
        "format": "WAV",
        "duration": duration,
        "sample_rate": rate,
        "channels": channels,
        "rms": rms,
    }


def _pcm_rms(raw: bytes, sample_width: int) -> float:
    if not raw:
        return 0.0
    if sample_width == 1:
        vals = [b - 128 for b in raw]
    elif sample_width == 2:
        vals = struct.unpack("<" + "h" * (len(raw) // 2), raw[:len(raw) // 2 * 2])
    else:
        return 1.0 if any(raw) else 0.0
    return math.sqrt(sum(v * v for v in vals) / max(1, len(vals)))


def _ffprobe_audio_info(path: Path) -> dict:
    data = _ffprobe(path)
    streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    if not streams:
        raise ArtifactValidationError(f"no audio stream found in {path}")
    stream = streams[0]
    duration = float(stream.get("duration") or data.get("format", {}).get("duration") or 0.0)
    return {
        "kind": "audio",
        "format": path.suffix.upper().lstrip("."),
        "duration": duration,
        "sample_rate": int(stream.get("sample_rate") or 0),
        "channels": int(stream.get("channels") or 0),
        "rms": 1.0,
    }


def _ffprobe_video_info(path: Path) -> dict:
    data = _ffprobe(path)
    videos = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    if not videos:
        raise ArtifactValidationError(f"no video stream found in {path}")
    video = videos[0]
    fps = _fraction(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1")
    duration = float(video.get("duration") or data.get("format", {}).get("duration") or 0.0)
    nb_frames = video.get("nb_frames")
    frames = int(nb_frames) if nb_frames else int(round(duration * fps)) if fps else 0
    return {
        "kind": "video",
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "fps": fps,
        "duration": duration,
        "frame_count": frames,
        "has_audio": any(s.get("codec_type") == "audio" for s in data.get("streams", [])),
    }


def _ffprobe(path: Path) -> dict:
    try:
        out = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            ],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except FileNotFoundError as exc:
        raise ArtifactValidationError("ffprobe is required for this artifact type") from exc
    except subprocess.CalledProcessError as exc:
        raise ArtifactValidationError(f"ffprobe failed for {path}: {exc.output}") from exc
    return json.loads(out)


def _fraction(value: str) -> float:
    if "/" in value:
        num, den = value.split("/", 1)
        den_f = float(den or 1)
        return float(num) / den_f if den_f else 0.0
    return float(value or 0.0)


def _close(actual: float, expected: float, tolerance: float) -> bool:
    return abs(float(actual) - float(expected)) <= tolerance
