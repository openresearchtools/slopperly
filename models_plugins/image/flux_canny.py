"""FLUX.1 Canny control generation via local ComfyUI."""

from ...models.base import ModelInputs, ModelPlugin, InputSpec, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, solve_path


WORKFLOW_ID = "flux1_canny_control"
_MUTATOR_ATTR = "_slopperly_comfy_workflow_mutator"


class FluxCannyPlugin(ModelPlugin):
    MODEL_ID     = "fuliucansheng/FLUX.1-Canny-dev-diffusers-lora"
    DISPLAY_NAME = "Image: FLUX Canny ControlNet"
    MODEL_TYPE   = "image"
    DESCRIPTION  = "Edge-guided generation through local ComfyUI FLUX.1 Canny"

    INPUTS       = InputSpec.PROMPT | InputSpec.IMAGE | InputSpec.LORA
    UI_SECTIONS  = [
        UISection.PROMPT, UISection.IMAGE_STRIP,
        UISection.RESOLUTION, UISection.FRAMES, UISection.STEPS, UISection.GUIDANCE,
        UISection.IMAGE_STRENGTH, UISection.SEED,
        UISection.LORA,
    ]
    PARAMS       = ParamSpec(steps=28, guidance=3.5)
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
        if inputs.image is None:
            raise ValueError("FLUX Canny requires an input image.")

        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        custom_loras = pipe_obj.get("enabled_loras", []) if isinstance(pipe_obj, dict) else []
        applied_loras = _set_flux1_lora_mutator(
            inputs,
            custom_loras,
            model_source_node="4",
            sampler_node="11",
        )
        if applied_loras:
            self._append_usage_note(
                inputs,
                f"FLUX.1 Canny applied {applied_loras} selected LoRA(s) through "
                "local ComfyUI LoraLoaderModelOnly.",
            )
        self._append_usage_note(
            inputs,
            "The official FLUX.1 Canny Comfy graph uses InstructPixToPixConditioning "
            "and does not expose a separate conditioning-strength input; the image "
            "strength slider is preserved in the UI and recorded as unmapped.",
        )

        inputs.flux1_canny_model = "flux1-canny-dev-fp16-Q5_0-GGUF.gguf"
        inputs.flux1_canny_clip_l = "clip_l.safetensors"
        inputs.flux1_canny_t5 = "t5xxl_fp16.safetensors"
        inputs.flux1_canny_clip_type = "flux"
        inputs.flux1_canny_vae = "ae.safetensors"
        inputs.flux1_canny_negative_prompt = ""
        inputs.flux1_canny_flux_guidance = float(inputs.guidance or 3.5)
        inputs.flux1_canny_cfg = 1.0
        inputs.flux1_canny_sampler = "euler"
        inputs.flux1_canny_scheduler = "normal"
        inputs.flux1_canny_denoise = 1.0
        inputs.flux1_canny_low_threshold = 50
        inputs.flux1_canny_high_threshold = 200
        inputs.flux1_canny_resolution = int(inputs.width or 1024)

        self.set_phase(inputs, f"Generating with local ComfyUI {self.DISPLAY_NAME}")
        filename = clean_filename(f"{inputs.seed}_flux1_canny_control") or "flux1_canny_control"
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
            _clear_flux1_lora_mutator(inputs)

    @staticmethod
    def _append_usage_note(inputs: ModelInputs, message: str) -> None:
        prefix = (getattr(inputs, "usage_note", "") + "\n") if getattr(inputs, "usage_note", "") else ""
        inputs.usage_note = prefix + message


def _set_flux1_lora_mutator(
    inputs: ModelInputs,
    enabled_loras,
    *,
    model_source_node: str,
    sampler_node: str,
) -> int:
    loras = _normalise_comfy_loras(enabled_loras)
    if not loras:
        return 0

    def _mutate(workflow, _schema, _inputs, _scene):
        return _inject_flux1_lora_chain(
            workflow,
            loras,
            model_source_node=model_source_node,
            sampler_node=sampler_node,
        )

    setattr(inputs, _MUTATOR_ATTR, _mutate)
    return len(loras)


def _clear_flux1_lora_mutator(inputs: ModelInputs) -> None:
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


def _inject_flux1_lora_chain(
    workflow: dict,
    loras: list[tuple[str, float]],
    *,
    model_source_node: str,
    sampler_node: str,
) -> dict:
    previous_model = [model_source_node, 0]
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
