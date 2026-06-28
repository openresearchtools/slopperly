"""Text-to-image via the local ComfyUI Krea 2 RAW/base workflow."""

from ...models.base import ModelInputs, ModelPlugin, InputSpec, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, solve_path


WORKFLOW_ID = "krea2_base_t2i"
_MUTATOR_ATTR = "_slopperly_comfy_workflow_mutator"


class Krea2BasePlugin(ModelPlugin):
    MODEL_ID = "ethanfel/Krea-2-Base-Diffusers"
    DISPLAY_NAME = "Image: Krea 2"
    DESCRIPTION = "High-quality text-to-image via the local ComfyUI Krea 2 RAW Q5 GGUF workflow"
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
        applied_loras = _set_krea_lora_mutator(inputs, custom_loras)
        if applied_loras:
            _append_usage_note(
                inputs,
                f"Krea 2 RAW applied {applied_loras} selected LoRA(s) through local "
                "ComfyUI LoraLoaderModelOnly.",
            )

        _prepare_krea_inputs(
            inputs,
            model_name="krea2_raw-Q5_K_M.gguf",
            steps_default=self.PARAMS.steps,
            guidance_default=self.PARAMS.guidance,
            turbo=False,
        )
        self.set_phase(inputs, "Generating with local ComfyUI Krea 2")
        filename = clean_filename(f"{inputs.seed}_krea2_base") or "krea2_base"
        destination = solve_path(filename + ".png")
        try:
            return gateway.run_comfy_workflow(
                WORKFLOW_ID,
                inputs,
                scene,
                prefs,
                destination=destination,
                timeout=float(getattr(prefs, "comfyui_timeout", 3600.0) or 3600.0),
            )
        finally:
            _clear_krea_lora_mutator(inputs)


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
    inputs.krea_textgen_sampling_mode = "on"
    inputs.krea_textgen_temperature = 0.7
    inputs.krea_textgen_top_k = 64
    inputs.krea_textgen_top_p = 0.95
    inputs.krea_textgen_min_p = 0.05
    inputs.krea_textgen_repetition_penalty = 1.05
    inputs.krea_textgen_presence_penalty = 0.0
    inputs.krea_textgen_seed = int(inputs.seed or 0)
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


def _set_krea_lora_mutator(inputs: ModelInputs, enabled_loras) -> int:
    loras = _normalise_comfy_loras(enabled_loras)
    if not loras:
        return 0

    def _mutate(workflow, _schema, _inputs, _scene):
        return _inject_krea_lora_chain(workflow, loras)

    setattr(inputs, _MUTATOR_ATTR, _mutate)
    return len(loras)


def _clear_krea_lora_mutator(inputs: ModelInputs) -> None:
    if hasattr(inputs, _MUTATOR_ATTR):
        delattr(inputs, _MUTATOR_ATTR)


def _normalise_comfy_loras(enabled_loras) -> list[tuple[str, float]]:
    loras: list[tuple[str, float]] = []
    for raw_name, raw_weight in enabled_loras or []:
        name = _comfy_lora_filename(raw_name)
        if not name:
            continue
        weight = float(raw_weight if raw_weight is not None else 1.0)
        loras.append((name, weight))
    return loras


def _comfy_lora_filename(raw_name) -> str:
    name = str(raw_name or "").replace("\\", "/").strip().rsplit("/", 1)[-1]
    if not name:
        return ""
    lower = name.lower()
    if not lower.endswith((".safetensors", ".ckpt", ".pt")):
        name = f"{name}.safetensors"
    return name


def _inject_krea_lora_chain(workflow: dict, loras: list[tuple[str, float]]) -> dict:
    previous_model = ["1", 0]
    next_node_id = 90
    for lora_name, strength in loras:
        while str(next_node_id) in workflow:
            next_node_id += 1
        node_id = str(next_node_id)
        workflow[node_id] = {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": previous_model,
                "lora_name": lora_name,
                "strength_model": strength,
            },
        }
        previous_model = [node_id, 0]
        next_node_id += 1
    workflow["8"].setdefault("inputs", {})["model"] = previous_model
    return workflow


def _append_usage_note(inputs: ModelInputs, note: str) -> None:
    current = getattr(inputs, "usage_note", "")
    inputs.usage_note = (current + "\n" if current else "") + note
