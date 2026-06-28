"""Wan2.2 A14B text-to-video routed through owned local ComfyUI GGUF."""

from __future__ import annotations

import math
import subprocess
from pathlib import Path

from ...models.base import InputSpec, ModelInputs, ModelPlugin, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, solve_path


WORKFLOW_ID = "wan22_t2v_a14b_720p16_to24_gguf"
WAN_HIGH_MODEL = "HighNoise/Wan2.2-T2V-A14B-HighNoise-Q5_K_M.gguf"
WAN_LOW_MODEL = "LowNoise/Wan2.2-T2V-A14B-LowNoise-Q5_K_M.gguf"
WAN_TEXT_ENCODER = "umt5_xxl_wan_text_encoder.safetensors"
WAN_VAE = "wan_2.1_vae.safetensors"
WAN_HIGH_LORA = "wan2.2_t2v_lightx2v_4steps_lora_v1.1_high_noise.safetensors"
WAN_LOW_LORA = "wan2.2_t2v_lightx2v_4steps_lora_v1.1_low_noise.safetensors"
TARGET_FPS = 24.0
NATIVE_FPS = 16.0


def _safe_wan_a14b_dimensions(width: int, height: int) -> tuple[int, int]:
    if int(height or 0) > int(width or 0):
        return 720, 1280
    return 1280, 720


def _native_frames_for_target(target_frames: int) -> int:
    duration = max(1, int(target_frames or 25)) / TARGET_FPS
    return max(1, int(math.ceil(duration * NATIVE_FPS)))


def prepare_wan22_t2v_a14b_inputs(inputs: ModelInputs) -> None:
    width, height = _safe_wan_a14b_dimensions(inputs.width, inputs.height)
    target_frames = max(1, int(inputs.frames or 25))
    native_frames = _native_frames_for_target(target_frames)
    steps = max(2, int(inputs.steps or 4))
    split_step = max(1, min(steps - 1, steps // 2))

    inputs.width = width
    inputs.height = height
    inputs.wan_target_frames = target_frames
    inputs.wan_target_fps = TARGET_FPS
    inputs.frames = native_frames
    inputs.fps = NATIVE_FPS
    inputs.steps = steps

    inputs.wan_high_model = WAN_HIGH_MODEL
    inputs.wan_low_model = WAN_LOW_MODEL
    inputs.wan_text_encoder = WAN_TEXT_ENCODER
    inputs.wan_clip_type = "wan"
    inputs.wan_clip_device = "cpu"
    inputs.wan_vae = WAN_VAE
    inputs.wan_vae_device = "cuda:0"
    inputs.wan_compute_device = "cuda:0"
    inputs.wan_virtual_vram_gb = 0.0
    inputs.wan_donor_device = "cpu"
    inputs.wan_expert_allocations = "cuda:0,1gb;cpu,*"
    inputs.wan_eject_models = True
    inputs.wan_high_lora = WAN_HIGH_LORA
    inputs.wan_low_lora = WAN_LOW_LORA
    inputs.wan_lora_strength = 1.0
    inputs.wan_shift = 5.0
    inputs.wan_sampler = "euler"
    inputs.wan_scheduler = "simple"
    inputs.wan_high_end_step = split_step
    inputs.wan_low_end_step = steps
    inputs.wan_video_format = "mp4"
    inputs.wan_video_codec = "h264"
    inputs.wan_output_prefix = "video/slopperly_wan22_t2v_a14b_native16"


class WanT2VPlugin(ModelPlugin):
    MODEL_ID = "Wan-AI/Wan2.2-T2V-A14B"
    DISPLAY_NAME = "Video: Wan2.2 T2V A14B (Local Q5)"
    MODEL_TYPE = "video"
    DESCRIPTION = "Local Wan2.2 A14B text-to-video through ComfyUI-GGUF, 16fps native to 24fps final MP4."

    INPUTS = InputSpec.PROMPT | InputSpec.NEG_PROMPT | InputSpec.LORA
    UI_SECTIONS = [
        UISection.PROMPT,
        UISection.NEG_PROMPT,
        UISection.RESOLUTION,
        UISection.FRAMES,
        UISection.STEPS,
        UISection.GUIDANCE,
        UISection.SEED,
        UISection.LORA,
    ]
    PARAMS = ParamSpec(width=1280, height=720, frames=25, steps=4, guidance=1.0)
    REQUIRED_PACKAGES = []
    supports_batch = False

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

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        prepare_wan22_t2v_a14b_inputs(inputs)
        if isinstance(pipe_obj, dict) and pipe_obj.get("enabled_loras"):
            _append_usage_note(
                inputs,
                "Wan2.2 A14B T2V Q5 uses the committed high/low Lightx2v LoRAs; "
                "project LoRA adapters remain visible but need separate artifact certification.",
            )
        _append_usage_note(
            inputs,
            (
                f"Wan2.2 A14B T2V Q5 generated {inputs.frames} native frames at "
                f"{NATIVE_FPS:g}fps and finalized the returned MP4 at {TARGET_FPS:g}fps."
            ),
        )

        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        stem = clean_filename(str(inputs.seed) + "_" + (inputs.prompt[:30] or "wan22_t2v_a14b"))
        destination = Path(solve_path(stem + ".mp4"))
        native_destination = destination.with_name(destination.stem + "_native16.mp4")

        self.set_phase(inputs, f"Running local Comfy workflow: {WORKFLOW_ID}")
        native_path = gateway.run_comfy_workflow(
            WORKFLOW_ID,
            inputs,
            scene,
            prefs,
            destination=str(native_destination),
            timeout=float(getattr(prefs, "comfyui_timeout", 7200.0) or 7200.0),
        )
        self.set_phase(inputs, "Finalizing Wan2.2 A14B T2V output at 24fps")
        _finalize_native_16fps_to_24fps(Path(native_path), destination)
        return str(destination)


def _finalize_native_16fps_to_24fps(native_path: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(native_path),
        "-map",
        "0:v:0",
        "-vf",
        f"fps={TARGET_FPS:g},setsar=1,format=yuv420p",
        "-r",
        f"{TARGET_FPS:g}",
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(destination),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is required to finalize Wan2.2 A14B T2V output") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(f"ffmpeg failed to finalize Wan2.2 A14B T2V output: {detail}") from exc


def _append_usage_note(inputs: ModelInputs, note: str) -> None:
    current = getattr(inputs, "usage_note", "")
    inputs.usage_note = (current + "\n" if current else "") + note
