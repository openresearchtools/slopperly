"""Timing helpers for audio-driven local video workflows."""

from __future__ import annotations

import json
import math
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

from .errors import WorkflowValidationError


@dataclass(frozen=True)
class AudioDrivenVideoPlan:
    audio_duration_seconds: float
    target_fps: float
    workflow_native_fps: float
    target_frames: int
    native_frames: int
    final_duration_seconds: float
    generated_duration_seconds: float

    def log_fields(self) -> dict:
        return {
            "audio_duration_seconds": self.audio_duration_seconds,
            "target_fps": self.target_fps,
            "workflow_native_fps": self.workflow_native_fps,
            "target_frames": self.target_frames,
            "native_frames": self.native_frames,
            "final_duration_seconds": self.final_duration_seconds,
            "generated_duration_seconds": self.generated_duration_seconds,
        }


def probe_audio_duration(path: str | Path) -> float:
    """Return audio duration in seconds using WAV metadata or ffprobe."""
    audio_path = Path(path)
    if not audio_path.is_file():
        raise WorkflowValidationError(f"audio file does not exist: {audio_path}")
    if audio_path.suffix.lower() == ".wav":
        with wave.open(str(audio_path), "rb") as wav:
            rate = wav.getframerate()
            if rate <= 0:
                raise WorkflowValidationError(f"WAV has invalid sample rate: {audio_path}")
            return wav.getnframes() / float(rate)
    return _ffprobe_duration(audio_path)


def plan_audio_driven_video(
    *,
    audio_path: str | Path | None = None,
    requested_frames: int = 0,
    target_fps: float = 24.0,
    workflow_native_fps: float | None = None,
) -> AudioDrivenVideoPlan:
    """Compute native/final frame counts for dialogue or lipsync video.

    If audio is present, audio duration is authoritative. Without audio, the
    requested frame count defines duration so non-dialogue paths still get the
    same diagnostic shape.
    """
    if target_fps <= 0:
        raise WorkflowValidationError(f"target_fps must be positive, got {target_fps}")
    native_fps = float(workflow_native_fps or target_fps)
    if native_fps <= 0:
        raise WorkflowValidationError(f"workflow_native_fps must be positive, got {native_fps}")

    if audio_path:
        duration = probe_audio_duration(audio_path)
    elif requested_frames > 0:
        duration = requested_frames / float(target_fps)
    else:
        raise WorkflowValidationError("audio_path or requested_frames is required for timing")

    target_frames = max(1, math.ceil(duration * float(target_fps)))
    native_frames = max(1, math.ceil(duration * native_fps))
    return AudioDrivenVideoPlan(
        audio_duration_seconds=duration,
        target_fps=float(target_fps),
        workflow_native_fps=native_fps,
        target_frames=target_frames,
        native_frames=native_frames,
        final_duration_seconds=duration,
        generated_duration_seconds=native_frames / native_fps,
    )


def _ffprobe_duration(path: Path) -> float:
    try:
        out = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(path),
            ],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except FileNotFoundError as exc:
        raise WorkflowValidationError("ffprobe is required for non-WAV audio duration") from exc
    except subprocess.CalledProcessError as exc:
        raise WorkflowValidationError(f"ffprobe failed for {path}: {exc.output}") from exc
    try:
        duration = float(json.loads(out).get("format", {}).get("duration") or 0.0)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise WorkflowValidationError(f"ffprobe returned invalid duration for {path}") from exc
    if duration <= 0:
        raise WorkflowValidationError(f"ffprobe returned no duration for {path}")
    return duration
