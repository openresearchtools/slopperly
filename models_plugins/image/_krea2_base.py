"""Text-to-image via the local ComfyUI Krea 2 RAW/base workflow."""

from ...models.base import ModelInputs, ModelPlugin, InputSpec, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, solve_path


WORKFLOW_ID = "krea2_base_t2i"


class Krea2BasePlugin(ModelPlugin):
    MODEL_ID = "ethanfel/Krea-2-Base-Diffusers"
    DISPLAY_NAME = "Image: Krea 2"
    DESCRIPTION = "High-quality text-to-image via the local ComfyUI Krea 2 RAW workflow"
    MODEL_TYPE = "image"
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
    PARAMS = ParamSpec(steps=28, guidance=4.5)
    REQUIRED_PACKAGES = []
    supports_inpaint = False
    supports_img2img = False
    uses_standard_input_strip = False

    def load(self, prefs, scene, **kw):
        enabled = [
            (getattr(item, "name", ""), float(getattr(item, "weight_value", 1.0) or 1.0))
            for item in kw.get("enabled_items", [])
            if getattr(item, "enabled", True) and getattr(item, "name", "")
        ]
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "last_model_card": self.MODEL_ID,
            "enabled_loras": enabled,
        }

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        custom_loras = pipe_obj.get("enabled_loras", []) if isinstance(pipe_obj, dict) else []
        if custom_loras:
            inputs.usage_note = (
                (getattr(inputs, "usage_note", "") + "\n")
                if getattr(inputs, "usage_note", "")
                else ""
            ) + (
                "Krea 2 RAW local Comfy workflow preserves the LoRA UI, but dynamic "
                "project LoRA injection is not mapped in this certified graph yet."
            )

        _prepare_krea_inputs(
            inputs,
            model_name="krea2_raw_fp8_scaled.safetensors",
            steps_default=self.PARAMS.steps,
            guidance_default=self.PARAMS.guidance,
            turbo=False,
        )
        self.set_phase(inputs, "Generating with local ComfyUI Krea 2")
        filename = clean_filename(f"{inputs.seed}_krea2_base") or "krea2_base"
        destination = solve_path(filename + ".png")
        return gateway.run_comfy_workflow(
            WORKFLOW_ID,
            inputs,
            scene,
            prefs,
            destination=destination,
            timeout=float(getattr(prefs, "comfyui_timeout", 3600.0) or 3600.0),
        )


def _prepare_krea_inputs(
    inputs: ModelInputs,
    *,
    model_name: str,
    steps_default: int,
    guidance_default: float,
    turbo: bool,
):
    inputs.krea_model = model_name
    inputs.krea_text_encoder = "qwen3vl_4b_fp8_scaled.safetensors"
    inputs.krea_clip_type = "krea2"
    inputs.krea_vae = "qwen_image_vae.safetensors"
    inputs.krea_sampler = "euler"
    inputs.krea_scheduler = "simple"
    inputs.krea_denoise = 1.0
    inputs.krea_guidance = float(inputs.guidance or guidance_default)
    inputs.krea_steps = int(inputs.steps or steps_default)
    inputs.krea_prompt_request = _prompt_enhancement_request(inputs, turbo=turbo)
    inputs.krea_textgen_max_length = 512
    inputs.krea_textgen_sampling_mode = {
        "sampling_mode": "on",
        "temperature": 0.7,
        "top_k": 64,
        "top_p": 0.95,
        "min_p": 0.05,
        "repetition_penalty": 1.05,
        "presence_penalty": 0.0,
        "seed": int(inputs.seed or 0),
    }
    inputs.krea_textgen_thinking = False
    inputs.krea_textgen_use_default_template = True


def _prompt_enhancement_request(inputs: ModelInputs, *, turbo: bool) -> str:
    prompt = (inputs.prompt or "").replace("{", "{{").replace("}", "}}")
    variant = "Krea 2 Turbo" if turbo else "Krea 2 RAW"
    return (
        "You are an expert prompt engineer for local text-to-image generation. "
        f"Polish the user's prompt for {variant} while preserving the subject, "
        "composition, medium, colors, and any requested visible text exactly. "
        "Return one concise image prompt paragraph and no labels.\n\n"
        f'User prompt: "{prompt}"\n'
        f"Target size: {int(inputs.width)}x{int(inputs.height)}"
    )
