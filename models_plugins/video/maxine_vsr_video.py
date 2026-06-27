"""Local video super-resolution through a ComfyUI upscale workflow."""

import subprocess
from fractions import Fraction

from ...models.base import ModelPlugin, InputSpec, UISection, ParamSpec, ModelInputs
from ...utils.helpers import clean_filename, solve_path
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway


def _parse_rate(value: str) -> float | None:
    text = str(value or "").strip()
    if not text or text == "0/0":
        return None
    try:
        if "/" in text:
            rate = float(Fraction(text))
        else:
            rate = float(text)
    except (ValueError, ZeroDivisionError):
        return None
    return rate if rate > 0 else None


def _probe_video_fps(path: str, default: float) -> float:
    fallback = float(default or 24.0)
    try:
        output = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=avg_frame_rate,r_frame_rate",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=10,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return fallback
    for line in output.splitlines():
        parsed = _parse_rate(line)
        if parsed:
            return parsed
    return fallback


class MaxineVSRVideoPlugin(ModelPlugin):
    MODEL_ID     = "nvidia/maxine-vsr-video"
    DISPLAY_NAME = "Video: Local Super Resolution"
    MODEL_TYPE   = "video"
    DESCRIPTION  = "Local ComfyUI video super-resolution using Real-ESRGAN"

    INPUTS      = InputSpec.VIDEO
    UI_SECTIONS = [UISection.VIDEO_STRIP, UISection.RESOLUTION, UISection.SEED]
    PARAMS      = ParamSpec()

    REQUIRED_PACKAGES          = []
    supports_inpaint           = False
    supports_img2img           = False
    requires_input_strip       = True
    uses_standard_input_strip  = False
    show_enhance               = False
    supports_batch             = False

    def load(self, prefs, scene, **kw):
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "last_model_card": self.MODEL_ID,
        }

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        video_path = inputs.video_path
        if not video_path:
            raise ValueError("Local Video Super Resolution requires an input video strip.")

        inputs.fps = _probe_video_fps(video_path, getattr(inputs, "fps", 24.0))

        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        self.set_phase(inputs, "Upscaling video with local ComfyUI")
        filename = clean_filename(f"{inputs.seed}_local_video_super_resolution")
        if not filename:
            filename = "local_video_super_resolution"
        destination = solve_path(filename + ".mp4")
        return gateway.run_comfy_workflow(
            "local_video_vsr_upscale",
            inputs,
            scene,
            prefs,
            destination=destination,
            timeout=float(getattr(prefs, "comfyui_timeout", 3600.0) or 3600.0),
        )
