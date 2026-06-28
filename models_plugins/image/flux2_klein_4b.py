"""Text-to-image and reference image editing via local ComfyUI FLUX.2 Klein 4B."""

from pathlib import Path

from ...models.base import ModelInputs, ModelPlugin, InputSpec, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, find_strip_by_name, get_strip_path, solve_path


T2I_WORKFLOW_ID = "flux2_klein_4b_t2i_edit"
EDIT_WORKFLOW_ID = "flux2_klein_4b_t2i_edit_img2img"
_MUTATOR_ATTR = "_slopperly_comfy_workflow_mutator"


class Flux2Klein4BPlugin(ModelPlugin):
    MODEL_ID     = "black-forest-labs/FLUX.2-klein-4B"
    DISPLAY_NAME = "Image: FLUX.2 Klein 4B"
    DESCRIPTION  = "Text-to-image and reference editing via local ComfyUI FLUX.2 Klein 4B"
    MODEL_TYPE   = "image"
    INPUTS       = InputSpec.PROMPT | InputSpec.IMAGE | InputSpec.LORA
    UI_SECTIONS  = [
        UISection.PROMPT, UISection.IMAGE_STRIP,
        UISection.RESOLUTION, UISection.FRAMES, UISection.STEPS, UISection.GUIDANCE,
        UISection.IMAGE_STRENGTH, UISection.SEED,
        UISection.LORA,
    ]
    PARAMS            = ParamSpec(steps=4, guidance=1.0)
    REQUIRED_PACKAGES = []
    supports_inpaint       = True
    inpaint_uses_strength  = True
    supports_img2img       = True

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

    def draw_custom_ui(self, col, context) -> bool:
        scene = context.scene
        try:
            col.prop(scene, "input_strips", text="Input")
        except Exception:
            pass
        if scene.sequence_editor is None:
            return True
        for attr, action in [
            ("klein_strip_1", "klein_select1"),
            ("klein_strip_2", "klein_select2"),
            ("klein_strip_3", "klein_select3"),
        ]:
            row = col.row(align=True)
            row.prop_search(
                scene, attr, scene.sequence_editor, "strips",
                text="Ref.", icon="FILE_IMAGE",
            )
            row.operator("sequencer.strip_picker", text="", icon="EYEDROPPER").action = action
        return True

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        inputs.flux2_klein_model = "flux-2-klein-4b-Q5_K_M.gguf"
        inputs.flux2_klein_text_encoder = "qwen_3_4b.safetensors"
        inputs.flux2_klein_clip_type = "flux2"
        inputs.flux2_klein_vae = "flux2-vae.safetensors"
        inputs.flux2_klein_sampler = "euler"
        inputs.flux2_klein_guidance = float(inputs.guidance or 1.0)

        workflow_id = T2I_WORKFLOW_ID
        stem = "flux2_klein_4b"
        unet_node = "1"
        guider_node = "6"
        if inputs.mode in {"img2img", "inpaint"} and inputs.image is not None:
            workflow_id = EDIT_WORKFLOW_ID
            stem = "flux2_klein_4b_edit"
            unet_node = "3"
            guider_node = "11"
            if inputs.mode == "inpaint":
                self._append_usage_note(
                    inputs,
                    "The committed FLUX.2 Klein 4B Comfy graph uses the official "
                    "reference-edit workflow. Masked inpaint is preserved in the UI but "
                    "blocked until an official local mask workflow is certified.",
                )
            self._prepare_reference_images(inputs, scene)
            self._append_usage_note(
                inputs,
                "The official FLUX.2 Klein reference-edit workflow does not expose a "
                "denoise/strength input; the image-strength slider is kept visible and "
                "recorded as unmapped for this certified graph.",
            )

        custom_loras = pipe_obj.get("enabled_loras", []) if isinstance(pipe_obj, dict) else []
        applied_loras = _set_flux2_klein_lora_mutator(
            inputs,
            custom_loras,
            unet_node=unet_node,
            guider_node=guider_node,
        )
        if applied_loras:
            self._append_usage_note(
                inputs,
                f"FLUX.2 Klein 4B applied {applied_loras} selected LoRA(s) through "
                "local ComfyUI LoraLoaderModelOnly.",
            )

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
            _clear_flux2_klein_lora_mutator(inputs)

    def _prepare_reference_images(self, inputs: ModelInputs, scene) -> None:
        images = []
        if getattr(inputs, "image", None) is not None:
            images.append(inputs.image)
        images.extend(self._scene_reference_paths(scene))
        images = [image for image in images if image][:3]
        if not images:
            raise ValueError(
                "FLUX.2 Klein 4B reference editing requires an image input. "
                "Select an image or movie strip and set Input to 'Strip', "
                "or pick strips using the Klein reference selectors."
            )
        inputs.images = images

    def _scene_reference_paths(self, scene) -> list[str]:
        paths: list[str] = []
        for path_attr, strip_attr in [
            ("klein_strip_1_path", "klein_strip_1"),
            ("klein_strip_2_path", "klein_strip_2"),
            ("klein_strip_3_path", "klein_strip_3"),
        ]:
            path = getattr(scene, path_attr, "") or ""
            if path and Path(path).is_file():
                paths.append(path)
                continue
            strip_name = getattr(scene, strip_attr, "") or ""
            if not strip_name:
                continue
            strip = find_strip_by_name(scene, strip_name)
            if strip is None:
                continue
            strip_path = get_strip_path(strip)
            if strip_path:
                paths.append(strip_path)
        return paths

    @staticmethod
    def _append_usage_note(inputs: ModelInputs, message: str) -> None:
        prefix = (getattr(inputs, "usage_note", "") + "\n") if getattr(inputs, "usage_note", "") else ""
        inputs.usage_note = prefix + message


def _set_flux2_klein_lora_mutator(
    inputs: ModelInputs,
    enabled_loras,
    *,
    unet_node: str,
    guider_node: str,
) -> int:
    loras = _normalise_comfy_loras(enabled_loras)
    if not loras:
        return 0

    def _mutate(workflow, _schema, _inputs, _scene):
        return _inject_flux2_klein_lora_chain(
            workflow,
            loras,
            unet_node=unet_node,
            guider_node=guider_node,
        )

    setattr(inputs, _MUTATOR_ATTR, _mutate)
    return len(loras)


def _clear_flux2_klein_lora_mutator(inputs: ModelInputs) -> None:
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


def _inject_flux2_klein_lora_chain(
    workflow: dict,
    loras: list[tuple[str, float]],
    *,
    unet_node: str,
    guider_node: str,
) -> dict:
    previous_model = [unet_node, 0]
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
    workflow[guider_node].setdefault("inputs", {})["model"] = previous_model
    return workflow
