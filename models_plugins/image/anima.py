"""Text-to-image and img2img via local ComfyUI Anima workflows."""

from ...models.base import ModelInputs, ModelPlugin, InputSpec, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, solve_path


T2I_WORKFLOW_ID = "anima_t2i_i2i"
I2I_WORKFLOW_ID = "anima_t2i_i2i_img2img"
_MUTATOR_ATTR = "_slopperly_comfy_workflow_mutator"


class AnimaPlugin(ModelPlugin):
    MODEL_ID     = "mrfatso/anima-preview3-diffusers"
    DISPLAY_NAME = "Image: Anima"
    MODEL_TYPE   = "image"
    DESCRIPTION  = "Anime-style generation via Anima with txt2img, img2img, and LoRA support"

    INPUTS       = InputSpec.PROMPT | InputSpec.NEG_PROMPT | InputSpec.IMAGE | InputSpec.LORA
    UI_SECTIONS  = [
        UISection.PROMPT, UISection.NEG_PROMPT, UISection.IMAGE_STRIP,
        UISection.RESOLUTION, UISection.FRAMES, UISection.STEPS, UISection.GUIDANCE,
        UISection.IMAGE_STRENGTH, UISection.SEED, UISection.LORA,
    ]
    PARAMS            = ParamSpec(steps=25, guidance=4.0)
    REQUIRED_PACKAGES = []
    supports_inpaint  = False
    supports_img2img  = True

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

        workflow_id = T2I_WORKFLOW_ID
        stem = "anima_preview3"
        sampler_node = "7"
        if inputs.mode == "img2img" and inputs.image is not None:
            workflow_id = I2I_WORKFLOW_ID
            stem = "anima_preview3_i2i"
            sampler_node = "9"
            inputs.anima_denoise = max(0.0, min(1.0, 1.0 - float(inputs.strength)))
        else:
            inputs.anima_denoise = 1.0

        custom_loras = pipe_obj.get("enabled_loras", []) if isinstance(pipe_obj, dict) else []
        applied_loras = _set_anima_lora_mutator(inputs, custom_loras, sampler_node=sampler_node)
        if applied_loras:
            _append_usage_note(
                inputs,
                f"Anima applied {applied_loras} selected LoRA(s) through local "
                "ComfyUI LoraLoaderModelOnly.",
            )

        inputs.anima_model = "anima-preview3-base.safetensors"
        inputs.anima_text_encoder = "qwen_3_06b_base.safetensors"
        inputs.anima_clip_type = "stable_diffusion"
        inputs.anima_vae = "qwen_image_vae.safetensors"
        inputs.anima_sampler = "er_sde"
        inputs.anima_scheduler = "simple"

        self.set_phase(inputs, f"Generating with local ComfyUI {self.DISPLAY_NAME}")
        filename = clean_filename(f"{inputs.seed}_{stem}") or stem
        destination = solve_path(filename + ".png")
        try:
            return gateway.run_comfy_workflow(
                workflow_id,
                inputs,
                scene,
                prefs,
                destination=destination,
                timeout=float(getattr(prefs, "comfyui_timeout", 3600.0) or 3600.0),
            )
        finally:
            _clear_anima_lora_mutator(inputs)


def _set_anima_lora_mutator(inputs: ModelInputs, enabled_loras, *, sampler_node: str) -> int:
    loras = _normalise_comfy_loras(enabled_loras)
    if not loras:
        return 0

    def _mutate(workflow, _schema, _inputs, _scene):
        return _inject_anima_lora_chain(workflow, loras, sampler_node=sampler_node)

    setattr(inputs, _MUTATOR_ATTR, _mutate)
    return len(loras)


def _clear_anima_lora_mutator(inputs: ModelInputs) -> None:
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


def _inject_anima_lora_chain(
    workflow: dict,
    loras: list[tuple[str, float]],
    *,
    sampler_node: str,
) -> dict:
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
    workflow[sampler_node].setdefault("inputs", {})["model"] = previous_model
    return workflow


def _append_usage_note(inputs: ModelInputs, note: str) -> None:
    current = getattr(inputs, "usage_note", "")
    inputs.usage_note = (current + "\n" if current else "") + note
