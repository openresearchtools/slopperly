"""Text-to-image via the local Slopperly ComfyUI Nucleus Image workflow."""

from pathlib import Path

from ...models.base import InputSpec, ModelInputs, ModelPlugin, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, solve_path


WORKFLOW_ID = "nucleus_image_t2i"
OWNED_COMFY_CACHE_DIR = ".slopperly/runtimes/ComfyUI"


class NucleusMoEPlugin(ModelPlugin):
    MODEL_ID = "NucleusAI/Nucleus-Image"
    FP8_REPO = "D-Squarius-Green-Jr/Nucleus-Image-FP8"
    DISPLAY_NAME = "Image: Nucleus Image"
    MODEL_TYPE = "image"
    DESCRIPTION = "High-quality text-to-image via the local Slopperly ComfyUI Nucleus Image workflow"

    INPUTS = InputSpec.PROMPT | InputSpec.NEG_PROMPT
    UI_SECTIONS = [
        UISection.PROMPT,
        UISection.NEG_PROMPT,
        UISection.RESOLUTION,
        UISection.FRAMES,
        UISection.STEPS,
        UISection.GUIDANCE,
        UISection.SEED,
    ]
    PARAMS = ParamSpec(steps=20, guidance=8.0)
    REQUIRED_PACKAGES = []
    supports_inpaint = False
    supports_img2img = False
    uses_standard_input_strip = False

    def load(self, prefs, scene, **kw):
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "last_model_card": self.MODEL_ID,
        }

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        _prepare_nucleus_inputs(inputs, prefs)
        self.set_phase(inputs, "Generating with local ComfyUI Nucleus Image")
        filename = clean_filename(f"{inputs.seed}_nucleus_image") or "nucleus_image"
        destination = solve_path(filename + ".png")
        return gateway.run_comfy_workflow(
            WORKFLOW_ID,
            inputs,
            scene,
            prefs,
            destination=destination,
            timeout=float(getattr(prefs, "comfyui_timeout", 3600.0) or 3600.0),
        )


def _prepare_nucleus_inputs(inputs: ModelInputs, prefs) -> None:
    cache_root = _model_cache_root(prefs)
    base_dir = cache_root / "models" / "diffusers" / "nucleus_image_base"
    fp8_dir = cache_root / "models" / "diffusers" / "nucleus_image_fp8"

    inputs.nucleus_model_id = NucleusMoEPlugin.MODEL_ID
    inputs.nucleus_model_path = str(base_dir)
    inputs.nucleus_fp8_patch_path = str(fp8_dir / "moe_fp8_patch.py")
    inputs.nucleus_fp8_weights_path = str(fp8_dir / "Nucleus-Image-FP8.safetensors")
    inputs.nucleus_local_files_only = True


def _model_cache_root(prefs) -> Path:
    configured = getattr(prefs, "slopperly_model_cache", "") or ""
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path(__file__).resolve().parents[2] / OWNED_COMFY_CACHE_DIR).resolve()
