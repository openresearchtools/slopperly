"""Saved-project video alias routed to local Wan/LTX workflow profiles."""

from ...models.base import InputSpec, ModelInputs, ModelPlugin, ParamSpec, UISection
from ...utils.helpers import clean_filename, solve_path
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway


class GoogleVeoPlugin(ModelPlugin):
    MODEL_ID = "google/veo"
    DISPLAY_NAME = "Video: Local Wan/LTX (legacy alias)"
    MODEL_TYPE = "video"
    DESCRIPTION = (
        "Hidden compatibility alias for saved projects; production dropdowns use "
        "local Wan or LTX entries."
    )
    INPUTS = InputSpec.PROMPT | InputSpec.NEG_PROMPT | InputSpec.IMAGE
    UI_SECTIONS = [UISection.PROMPT, UISection.NEG_PROMPT]
    PARAMS = ParamSpec(width=1280, height=704, steps=25, guidance=5.0)
    REQUIRED_PACKAGES = []
    production_visible = False
    alias_target = "wan22_ti2v_5b_720p24_gguf"

    supports_inpaint = False
    supports_img2img = True
    uses_strip_power = False
    supports_batch = False

    def load(self, prefs, scene, **kw):
        return {"pipe": None, "last_model_card": self.MODEL_ID}

    def _workflow_id(self, inputs: ModelInputs) -> str:
        if getattr(inputs, "last_image", None) is not None:
            return "wan22_flf2v_a14b_720p16_to24"
        if getattr(inputs, "image", None) is not None:
            return "wan22_ti2v_5b_720p24_gguf"
        return self.alias_target

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs) -> str:
        workflow_id = self._workflow_id(inputs)
        self.set_phase(inputs, f"Running local video alias: {workflow_id}")
        stem = clean_filename(str(inputs.seed) + "_" + (inputs.prompt[:30] or "local_video"))
        destination = solve_path(stem + ".mp4")
        return SlopperlyRuntimeGateway().run_comfy_workflow(
            workflow_id,
            inputs,
            scene,
            prefs,
            destination=destination,
        )
