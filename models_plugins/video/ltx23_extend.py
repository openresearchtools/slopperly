"""LTX 2.3 clip extension routed through owned local ComfyUI Q5 workflow."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ...models.base import InputSpec, ModelInputs, ModelPlugin, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, solve_path


WORKFLOW_ID = "ltx23_extend_staged"
LTX_GGUF_MODEL = "ltx-2.3-22b-distilled-1.1-Q5_K_M.gguf"
LTX_TEXT_ENCODER = "gemma_3_12B_it_fp4_mixed.safetensors"
LTX_CONNECTOR = "ltx-2.3-22b-distilled_embeddings_connectors.safetensors"
LTX_VIDEO_VAE = "ltx-2.3-22b-distilled_video_vae.safetensors"
LTX_AUDIO_VAE = "ltx-2.3-22b-distilled_audio_vae.safetensors"
LTX_LORA = "ltx-2.3-22b-distilled-lora-384.safetensors"


def _normalize_ltx_frames(frames: int) -> int:
    requested = max(9, int(frames or 17))
    return ((requested - 1) // 8) * 8 + 1


def _safe_ltx_dimensions(width: int, height: int) -> tuple[int, int]:
    safe_width = max(64, (int(width or 1280) // 32) * 32)
    safe_height = max(64, (int(height or 720) // 32) * 32)
    return safe_width, safe_height


def _probe_video(path: str | Path) -> dict:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=index,codec_type,width,height,r_frame_rate,duration",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffprobe is required for LTX local extension validation.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"ffprobe failed for {path}: {exc.stderr}") from exc
    data = json.loads(result.stdout or "{}")
    streams = data.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video:
        raise RuntimeError(f"LTX Extend source has no video stream: {path}")
    fps_num, _, fps_den = str(video.get("r_frame_rate") or "0/1").partition("/")
    fps = float(fps_num or 0) / float(fps_den or 1)
    duration = float(video.get("duration") or data.get("format", {}).get("duration") or 0.0)
    return {
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "fps": fps,
        "duration": duration,
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
    }


def _run_ffmpeg(args: list[str], action: str) -> None:
    try:
        subprocess.run(["ffmpeg", "-y", *args], check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is required for LTX local extension assembly.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"ffmpeg failed while {action}: {exc.stderr}") from exc


def _extract_last_frame(source: Path, frame_path: Path) -> None:
    frame_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _run_ffmpeg(
            [
                "-sseof",
                "-0.1",
                "-i",
                str(source),
                "-frames:v",
                "1",
                str(frame_path),
            ],
            "extracting the final source frame",
        )
    except RuntimeError:
        _run_ffmpeg(
            [
                "-i",
                str(source),
                "-vf",
                "select=eq(n\\,0)",
                "-frames:v",
                "1",
                str(frame_path),
            ],
            "extracting a fallback source frame",
        )
    if not frame_path.is_file() or frame_path.stat().st_size <= 0:
        raise RuntimeError(f"failed to extract LTX extension source frame: {frame_path}")


def _normalize_clip(source: Path, destination: Path, *, width: int, height: int, fps: float) -> dict:
    info = _probe_video(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    scale = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={fps},setsar=1,format=yuv420p"
    )
    video_args = [
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-r",
        f"{fps:.6f}",
        "-pix_fmt",
        "yuv420p",
    ]
    audio_args = ["-c:a", "aac", "-ar", "48000", "-ac", "2"]
    if info["has_audio"]:
        _run_ffmpeg(
            [
                "-i",
                str(source),
                "-vf",
                scale,
                "-af",
                "aresample=48000,aformat=channel_layouts=stereo",
                *video_args,
                *audio_args,
                "-movflags",
                "+faststart",
                str(destination),
            ],
            f"normalizing {source}",
        )
    else:
        duration = max(0.001, float(info["duration"] or 0.0))
        _run_ffmpeg(
            [
                "-i",
                str(source),
                "-f",
                "lavfi",
                "-t",
                f"{duration:.6f}",
                "-i",
                "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-vf",
                scale,
                *video_args,
                *audio_args,
                "-shortest",
                "-movflags",
                "+faststart",
                str(destination),
            ],
            f"normalizing {source} with silent audio",
        )
    return _probe_video(destination)


def _concat_normalized_clips(source: Path, tail: Path, destination: Path, *, fps: float) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    _run_ffmpeg(
        [
            "-i",
            str(source),
            "-i",
            str(tail),
            "-filter_complex",
            "[0:v:0][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[v][a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-r",
            f"{fps:.6f}",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(destination),
        ],
        "concatenating source clip and LTX extension tail",
    )
    return _probe_video(destination)


class LTX2_3ExtendStagedPlugin(ModelPlugin):
    MODEL_ID = "LTX-2.3 Extend Staged"
    DISPLAY_NAME = "Video: LTX-2.3 Extend (Local Q5)"
    MODEL_TYPE = "video"
    DESCRIPTION = "Extend a selected video clip with an owned ComfyUI LTX 2.3 Q5 GGUF tail workflow."

    INPUTS = InputSpec.PROMPT | InputSpec.NEG_PROMPT | InputSpec.IMAGE | InputSpec.LORA
    UI_SECTIONS = [
        UISection.PROMPT,
        UISection.NEG_PROMPT,
        UISection.VIDEO_STRIP,
        UISection.RESOLUTION,
        UISection.SEED,
        UISection.LORA,
    ]
    PARAMS = ParamSpec(width=1280, height=720, frames=17, steps=8, guidance=1.0, strength=0.7)
    REQUIRED_PACKAGES = []
    supports_inpaint = False
    uses_strip_power = False
    requires_main_thread_for_generate = False

    def draw_custom_ui(self, col, context) -> bool:
        scene = context.scene
        if scene.sequence_editor is not None:
            row = col.row(align=True)
            row.prop_search(
                scene,
                "ltx23ext_audio_strip",
                scene.sequence_editor,
                "strips",
                text="Audio Strip",
                icon="SEQ_STRIP_DUPLICATE",
            )
            row.operator("sequencer.strip_picker", text="", icon="EYEDROPPER").action = "ltx23ext_audio_select"
        col.prop(scene, "ltx23ext_extend_frames")
        col.prop(scene, "ltx23ext_video_strength")
        return False

    def draw_post_seed_ui(self, col, context):
        col.prop(context.scene, "ltx23_stage_mode")

    def load(self, prefs, scene, **kw):
        enabled_loras = [
            (getattr(item, "name", ""), float(getattr(item, "weight_value", 1.0) or 1.0))
            for item in kw.get("enabled_items", [])
            if getattr(item, "enabled", True) and getattr(item, "name", "")
        ]
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "enabled_loras": enabled_loras,
            "last_model_card": self.MODEL_ID,
        }

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs) -> str:
        source = _selected_video_path(inputs)
        if source is None:
            raise ValueError("LTX 2.3 Extend requires a selected input video strip.")
        source = source.resolve()

        width, height = _safe_ltx_dimensions(inputs.width, inputs.height)
        fps = float(getattr(inputs, "fps", 24.0) or 24.0)
        requested_extend = int(getattr(scene, "ltx23ext_extend_frames", 0) or inputs.frames or 17)
        tail_frames = _normalize_ltx_frames(requested_extend)
        strength = float(getattr(scene, "ltx23ext_video_strength", inputs.strength or 0.7) or 0.7)
        stage_mode = str(getattr(scene, "ltx23_stage_mode", "FULL") or "FULL")

        notes = []
        if stage_mode != "FULL":
            notes.append(
                "LTX Extend local Q5 certification uses the owned Comfy extension-tail path; "
                f"legacy stage mode {stage_mode!r} is preserved in the UI but not run through direct Diffusers."
            )
        custom_loras = pipe_obj.get("enabled_loras", []) if isinstance(pipe_obj, dict) else []
        if custom_loras:
            notes.append(
                "LTX Extend local Q5 workflow uses the committed distilled LTX LoRA; "
                "project LoRA adapters remain visible but are not dynamically injected yet."
            )
        if inputs.steps:
            notes.append("LTX Extend local Q5 workflow uses its committed ManualSigmas schedule.")
        if inputs.guidance:
            notes.append("LTX Extend local Q5 workflow uses BasicGuider without a direct CFG input.")
        if notes:
            inputs.usage_note = ((inputs.usage_note + "\n") if inputs.usage_note else "") + "\n".join(notes)

        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        filename = clean_filename(f"{inputs.seed}_ltx23_extend_q5") or "ltx23_extend_q5"
        destination = Path(solve_path(filename + ".mp4"))
        work_dir = destination.parent / f"{destination.stem}_parts"
        work_dir.mkdir(parents=True, exist_ok=True)
        last_frame = work_dir / "source_last_frame.png"
        tail_path = work_dir / "ltx23_extend_tail.mp4"
        normalized_source = work_dir / "source_normalized.mp4"
        normalized_tail = work_dir / "tail_normalized.mp4"

        self.set_phase(inputs, "Extracting source clip tail frame")
        _extract_last_frame(source, last_frame)

        tail_inputs = ModelInputs(
            prompt=inputs.prompt,
            neg_prompt=inputs.neg_prompt,
            image=str(last_frame),
            width=width,
            height=height,
            frames=tail_frames,
            fps=fps,
            steps=inputs.steps,
            guidance=inputs.guidance,
            strength=strength,
            seed=inputs.seed,
        )
        tail_inputs.ltx_model = LTX_GGUF_MODEL
        tail_inputs.ltx_text_encoder = LTX_TEXT_ENCODER
        tail_inputs.ltx_connector = LTX_CONNECTOR
        tail_inputs.ltx_video_vae = LTX_VIDEO_VAE
        tail_inputs.ltx_audio_vae = LTX_AUDIO_VAE
        tail_inputs.ltx_lora = LTX_LORA

        self.set_phase(inputs, f"Running local Comfy workflow: {WORKFLOW_ID}")
        gateway.run_comfy_workflow(
            WORKFLOW_ID,
            tail_inputs,
            scene,
            prefs,
            destination=str(tail_path),
            timeout=float(getattr(prefs, "comfyui_timeout", 7200.0) or 7200.0),
        )

        self.set_phase(inputs, "Assembling extended LTX clip")
        source_info = _normalize_clip(source, normalized_source, width=width, height=height, fps=fps)
        tail_info = _normalize_clip(tail_path, normalized_tail, width=width, height=height, fps=fps)
        final_info = _concat_normalized_clips(normalized_source, normalized_tail, destination, fps=fps)
        if final_info["duration"] <= source_info["duration"]:
            raise RuntimeError(
                "LTX Extend output duration did not grow: "
                f"source={source_info['duration']:.3f}s tail={tail_info['duration']:.3f}s "
                f"final={final_info['duration']:.3f}s"
            )
        return str(destination)


def _selected_video_path(inputs: ModelInputs) -> Path | None:
    for attr in ("video_path", "video", "video_ref"):
        value = getattr(inputs, attr, None)
        if value and isinstance(value, str):
            path = Path(value)
            if path.is_file():
                return path
    return None
