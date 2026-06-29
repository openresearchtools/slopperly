"""LTX 2.3 lipsync/dialogue routed through owned local ComfyUI Q5 workflow."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ...models.base import InputSpec, ModelInputs, ModelPlugin, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...slopperly.runtime.media_timing import plan_audio_driven_video
from ...utils.helpers import clean_filename, solve_path

try:
    from ...utils.helpers import load_first_frame
except ImportError:
    load_first_frame = None


WORKFLOW_ID = "ltx23_lipsync_dialogue"
LTX_GGUF_MODEL = "ltx-2.3-22b-distilled-1.1-Q5_K_M.gguf"
LTX_TEXT_ENCODER = "gemma_3_12B_it_fp4_mixed.safetensors"
LTX_CONNECTOR = "ltx-2.3-22b-distilled_embeddings_connectors.safetensors"
LTX_VIDEO_VAE = "ltx-2.3-22b-distilled_video_vae.safetensors"
LTX_AUDIO_VAE = "ltx-2.3-22b-distilled_audio_vae.safetensors"
LTX_LORA = "ltx-2.3-22b-distilled-lora-384.safetensors"


def _normalize_ltx_frames(frames: int) -> int:
    requested = max(9, int(frames or 17))
    return ((requested - 1 + 7) // 8) * 8 + 1


def _safe_ltx_dimensions(width: int, height: int) -> tuple[int, int]:
    safe_width = max(64, (int(width or 1280) // 32) * 32)
    safe_height = max(64, (int(height or 720) // 32) * 32)
    return safe_width, safe_height


def _selected_video_path(inputs: ModelInputs) -> Path | None:
    for attr in ("video_path", "video", "video_ref"):
        value = getattr(inputs, attr, None)
        if value and isinstance(value, str):
            path = Path(value)
            if path.is_file():
                return path
    return None


def _selected_audio_path(inputs: ModelInputs, scene) -> Path | None:
    for attr in ("audio_path", "audio", "audio_ref", "sound", "sound_path"):
        value = getattr(inputs, attr, None)
        if value and isinstance(value, str):
            path = Path(value)
            if path.is_file():
                return path
    scene_audio = getattr(scene, "ref_audio_path", "") if scene is not None else ""
    if scene_audio:
        path = Path(scene_audio)
        if path.is_file():
            return path
    video = _selected_video_path(inputs)
    return video


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
        raise RuntimeError("ffprobe is required for LTX lipsync validation.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"ffprobe failed for {path}: {exc.stderr}") from exc
    data = json.loads(result.stdout or "{}")
    streams = data.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video:
        raise RuntimeError(f"LTX lipsync output has no video stream: {path}")
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
        raise RuntimeError("ffmpeg is required for LTX lipsync audio assembly.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"ffmpeg failed while {action}: {exc.stderr}") from exc


def _finalize_dialogue_video(
    *,
    generated_video: Path,
    reference_audio: Path,
    destination: Path,
    width: int,
    height: int,
    fps: float,
    duration: float,
) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={fps:.6f},setsar=1,"
        f"tpad=stop_mode=clone:stop_duration={duration:.6f},"
        f"trim=duration={duration:.6f},setpts=PTS-STARTPTS,format=yuv420p"
    )
    af = (
        f"atrim=duration={duration:.6f},asetpts=PTS-STARTPTS,"
        "aresample=48000,aformat=channel_layouts=stereo"
    )
    _run_ffmpeg(
        [
            "-i",
            str(generated_video),
            "-i",
            str(reference_audio),
            "-filter_complex",
            f"[0:v:0]{vf}[v];[1:a:0]{af}[a]",
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
        "muxing LTX lipsync video with reference audio",
    )
    return _probe_video(destination)


class LTX2_3LipSyncPlugin(ModelPlugin):
    MODEL_ID = "LTX-2.3 Lip Sync"
    DISPLAY_NAME = "Video: LTX-2.3 Lip Sync (Local Q5)"
    MODEL_TYPE = "video"
    DESCRIPTION = "Local LTX 2.3 lipsync/dialogue through owned ComfyUI using a Q5 GGUF backbone."

    INPUTS = InputSpec.PROMPT | InputSpec.NEG_PROMPT | InputSpec.IMAGE | InputSpec.LORA | InputSpec.AUDIO_REF
    UI_SECTIONS = [
        UISection.PROMPT,
        UISection.NEG_PROMPT,
        UISection.VIDEO_STRIP,
        UISection.RESOLUTION,
        UISection.FRAMES,
        UISection.SEED,
        UISection.LORA,
    ]
    PARAMS = ParamSpec(width=1280, height=720, frames=25, steps=8, guidance=1.0, strength=0.7)
    REQUIRED_PACKAGES = []
    supports_inpaint = False
    requires_main_thread_for_generate = False

    def draw_custom_ui(self, col, context) -> bool:
        row = col.row(align=True)
        row.prop(context.scene, "ref_audio_path", text="Audio Ref.")
        row.operator("sequencer.open_audio_filebrowser", text="", icon="FILEBROWSER")
        return False

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
        audio_path = _selected_audio_path(inputs, scene)
        if audio_path is None:
            raise ValueError("LTX 2.3 Lip Sync requires an audio reference file or selected video with audio.")
        audio_path = audio_path.resolve()

        image = inputs.image
        video_path = _selected_video_path(inputs)
        if image is None and video_path is not None:
            if load_first_frame is None:
                raise ValueError("LTX lipsync video-strip input requires load_first_frame helper availability.")
            image = load_first_frame(str(video_path))
        if image is None:
            raise ValueError("LTX 2.3 Lip Sync requires a source image or selected video strip.")

        width, height = _safe_ltx_dimensions(inputs.width, inputs.height)
        fps = float(getattr(inputs, "fps", 24.0) or 24.0)
        timing = plan_audio_driven_video(
            audio_path=audio_path,
            requested_frames=int(inputs.frames or 0),
            target_fps=fps,
            workflow_native_fps=fps,
        )
        workflow_frames = _normalize_ltx_frames(timing.target_frames)
        strength = float(getattr(inputs, "strength", 0.7) or 0.7)
        identity_guidance = float(getattr(scene, "ltx23_lipsync_identity_guidance", 1.5) or 1.5)

        notes = []
        custom_loras = pipe_obj.get("enabled_loras", []) if isinstance(pipe_obj, dict) else []
        if custom_loras:
            notes.append(
                "LTX lipsync local Q5 workflow uses the committed distilled LTX LoRA; "
                "project LoRA adapters remain visible but are not dynamically injected yet."
            )
        if inputs.steps:
            notes.append("LTX lipsync local Q5 workflow uses its committed ManualSigmas schedule.")
        if inputs.guidance:
            notes.append("LTX lipsync local Q5 workflow uses BasicGuider without a direct CFG input.")
        if workflow_frames != timing.target_frames:
            notes.append(
                "LTX lipsync generation is rounded to 8n+1 frames in Comfy, then trimmed/padded "
                "to the reference audio duration during final local mux."
            )
        if notes:
            inputs.usage_note = ((inputs.usage_note + "\n") if inputs.usage_note else "") + "\n".join(notes)

        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        filename = clean_filename(f"{inputs.seed}_ltx23_lipsync_q5") or "ltx23_lipsync_q5"
        destination = Path(solve_path(filename + ".mp4"))
        work_dir = destination.parent / f"{destination.stem}_parts"
        work_dir.mkdir(parents=True, exist_ok=True)
        raw_path = work_dir / "ltx23_lipsync_raw.mp4"

        workflow_inputs = ModelInputs(
            prompt=inputs.prompt,
            neg_prompt=inputs.neg_prompt,
            image=image,
            audio_ref=str(audio_path),
            width=width,
            height=height,
            frames=workflow_frames,
            fps=fps,
            steps=inputs.steps,
            guidance=inputs.guidance,
            strength=strength,
            seed=inputs.seed,
        )
        workflow_inputs.ltx_model = LTX_GGUF_MODEL
        workflow_inputs.ltx_text_encoder = LTX_TEXT_ENCODER
        workflow_inputs.ltx_connector = LTX_CONNECTOR
        workflow_inputs.ltx_video_vae = LTX_VIDEO_VAE
        workflow_inputs.ltx_audio_vae = LTX_AUDIO_VAE
        workflow_inputs.ltx_lora = LTX_LORA
        workflow_inputs.ltx_reference_audio_guidance = identity_guidance

        self.set_phase(inputs, f"Running local Comfy workflow: {WORKFLOW_ID}")
        gateway.run_comfy_workflow(
            WORKFLOW_ID,
            workflow_inputs,
            scene,
            prefs,
            destination=str(raw_path),
            timeout=float(getattr(prefs, "comfyui_timeout", 7200.0) or 7200.0),
        )

        self.set_phase(inputs, "Muxing LTX lipsync reference audio")
        final_info = _finalize_dialogue_video(
            generated_video=raw_path,
            reference_audio=audio_path,
            destination=destination,
            width=width,
            height=height,
            fps=fps,
            duration=timing.final_duration_seconds,
        )
        if abs(final_info["duration"] - timing.final_duration_seconds) > 0.25:
            raise RuntimeError(
                "LTX lipsync output duration does not match reference audio: "
                f"video={final_info['duration']:.3f}s audio={timing.final_duration_seconds:.3f}s"
            )
        return str(destination)
