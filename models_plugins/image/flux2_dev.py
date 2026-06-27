"""Text-to-image and multi-reference generation via local ComfyUI FLUX.2 Dev."""

from pathlib import Path

from ...models.base import ModelInputs, ModelPlugin, InputSpec, ParamSpec, UISection
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import clean_filename, find_strip_by_name, get_strip_path, solve_path


T2I_WORKFLOW_ID = "flux2_dev_gguf_quality"
REF_WORKFLOW_ID = "flux2_dev_gguf_quality_refs"


class Flux2DevPlugin(ModelPlugin):
    MODEL_ID     = "diffusers/FLUX.2-dev-bnb-4bit"
    DISPLAY_NAME = "Image: FLUX.2 Dev (Q5 GGUF quality)"
    MODEL_TYPE   = "image"
    DESCRIPTION  = "Text-to-image and multi-reference generation via local ComfyUI FLUX.2 Dev Q5 GGUF"

    INPUTS       = InputSpec.PROMPT | InputSpec.MULTI_IMAGE
    UI_SECTIONS  = [
        UISection.PROMPT, UISection.MULTI_IMAGES,
        UISection.RESOLUTION, UISection.FRAMES, UISection.STEPS, UISection.GUIDANCE, UISection.SEED,
    ]
    PARAMS       = ParamSpec(steps=8, guidance=3.5)
    REQUIRED_PACKAGES = []
    supports_inpaint  = False
    supports_img2img  = False

    def load(self, prefs, scene, **kw):
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "last_model_card": self.MODEL_ID,
        }

    def draw_custom_ui(self, col, context) -> bool:
        scene = context.scene
        try:
            col.prop(scene, "input_strips", text="Input")
        except Exception:
            pass
        if scene.sequence_editor is None:
            return True
        for i in range(1, scene.flux_visible_strips + 1):
            row = col.row(align=True)
            row.prop_search(
                scene, f"flux_strip_{i}", scene.sequence_editor, "strips",
                text="Ref.", icon="FILE_IMAGE",
            )
            op = row.operator("sequencer.strip_picker", text="", icon="EYEDROPPER")
            op.action = f"flux_select{i}"
            if i == scene.flux_visible_strips and scene.flux_visible_strips < 9:
                if scene.flux_visible_strips > 1:
                    row.operator("object.flux_hide_strip", text="", icon="REMOVE").strip_index = i
                row.operator("object.flux_add_strip", text="", icon="ADD")
        return True

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        gateway = pipe_obj.get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        inputs.flux2_dev_model = "flux2-dev-Q5_K_M.gguf"
        inputs.flux2_dev_text_encoder = "mistral_3_small_flux2_fp8.safetensors"
        inputs.flux2_dev_clip_type = "flux2"
        inputs.flux2_dev_vae = "flux2-vae.safetensors"
        inputs.flux2_dev_sampler = "euler"
        inputs.flux2_dev_guidance = float(inputs.guidance or 3.5)

        workflow_id = T2I_WORKFLOW_ID
        stem = "flux2_dev_gguf_quality"
        ref_images = self._reference_images(inputs, scene)
        if ref_images:
            workflow_id = REF_WORKFLOW_ID
            stem = "flux2_dev_gguf_quality_refs"
            inputs.images = ref_images[:3]
            if len(ref_images) > 3:
                self._append_usage_note(
                    inputs,
                    "FLUX.2 Dev local Comfy quality workflow currently has three "
                    "certified ReferenceLatent slots. Extra selected FLUX references "
                    "remain visible in the UI but are not submitted until a larger "
                    "local graph is certified.",
                )

        self.set_phase(inputs, f"Generating with local ComfyUI {self.DISPLAY_NAME}")
        filename = clean_filename(f"{inputs.seed}_{stem}") or stem
        destination = solve_path(filename + ".png")
        return gateway.run_comfy_workflow(
            workflow_id,
            inputs,
            scene,
            prefs,
            destination=destination,
            timeout=float(getattr(prefs, "comfyui_timeout", 3600.0) or 3600.0),
        )

    def _reference_images(self, inputs: ModelInputs, scene) -> list:
        images = []
        if getattr(inputs, "image", None) is not None:
            images.append(inputs.image)
        images.extend(self._scene_reference_paths(scene))
        return [image for image in images if image]

    def _scene_reference_paths(self, scene) -> list[str]:
        paths: list[str] = []
        if scene is None:
            return paths
        for i in range(1, 10):
            path = getattr(scene, f"flux_strip_{i}_path", "") or ""
            if path and Path(path).is_file():
                paths.append(path)
                continue
            strip_name = getattr(scene, f"flux_strip_{i}", "") or ""
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
