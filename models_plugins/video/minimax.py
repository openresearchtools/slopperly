"""Saved-project MiniMax/Hailuo aliases routed to local video workflows."""

from ...models.base import InputSpec, ModelInputs, ModelPlugin, ParamSpec, UISection
from ...utils.helpers import clean_filename, solve_path
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway


class _MiniMaxBase(ModelPlugin):
    MODEL_TYPE = "video"
    INPUTS = InputSpec.PROMPT
    UI_SECTIONS = [UISection.PROMPT, UISection.FRAMES, UISection.SEED]
    PARAMS = ParamSpec(width=1280, height=704, steps=25, guidance=5.0)
    REQUIRED_PACKAGES = []
    uses_standard_input_strip = False
    supports_batch = False
    production_visible = False
    alias_target = "wan22_ti2v_5b_720p24_gguf"

    def load(self, prefs, scene, **kw):
        return {"pipe": None, "last_model_card": self.MODEL_ID}

    def _run_alias(self, inputs: ModelInputs, scene, prefs, workflow_id: str):
        self.set_phase(inputs, f"Running local video alias: {workflow_id}")
        stem = clean_filename((inputs.prompt or workflow_id)[:30]) or "local_video"
        destination = solve_path(stem + ".mp4")
        return SlopperlyRuntimeGateway().run_comfy_workflow(
            workflow_id,
            inputs,
            scene,
            prefs,
            destination=destination,
        )


class MiniMaxTxt2VidPlugin(_MiniMaxBase):
    MODEL_ID = "Hailuo/MiniMax/txt2vid"
    DISPLAY_NAME = "Video: Local Wan TI2V (legacy txt2vid alias)"
    DESCRIPTION = "Hidden saved-project alias for local Wan TI2V generation."

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        return self._run_alias(inputs, scene, prefs, self.alias_target)


class MiniMaxImg2VidPlugin(_MiniMaxBase):
    MODEL_ID = "Hailuo/MiniMax/img2vid"
    DISPLAY_NAME = "Video: Local Wan TI2V (legacy img2vid alias)"
    DESCRIPTION = "Hidden saved-project alias for local Wan image-conditioned generation."
    INPUTS = InputSpec.PROMPT | InputSpec.IMAGE

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        return self._run_alias(inputs, scene, prefs, self.alias_target)


class MiniMaxSubject2VidPlugin(_MiniMaxBase):
    MODEL_ID = "Hailuo/MiniMax/subject2vid"
    DISPLAY_NAME = "Video: Local Reference Video (legacy subject alias)"
    DESCRIPTION = "Hidden saved-project alias for local LTX reference-video generation."
    INPUTS = InputSpec.PROMPT | InputSpec.IMAGE
    alias_target = "ltx23_ic_lora_subject_i2v"

    def draw_custom_ui(self, col, context) -> bool:
        scene = context.scene
        if scene.sequence_editor is None:
            return False
        row = col.row(align=True)
        row.prop_search(
            scene,
            "minimax_subject",
            scene.sequence_editor,
            "strips",
            text="Subject",
            icon="USER",
        )
        row.operator("sequencer.strip_picker", text="", icon="EYEDROPPER").action = "minimax_select"
        return False

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs):
        return self._run_alias(inputs, scene, prefs, self.alias_target)
