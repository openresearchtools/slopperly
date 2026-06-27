"""Video-to-audio via the local Slopperly ComfyUI MMAudio workflow."""

from pathlib import Path

from ...models.base import ModelPlugin, InputSpec, UISection, ParamSpec, ModelInputs
from ...slopperly.runtime.gateway import SlopperlyRuntimeGateway
from ...utils.helpers import solve_path, clean_filename


WORKFLOW_ID = "mmaudio_video_to_audio"


class MMAudioPlugin(ModelPlugin):
    MODEL_ID = "MMAudio"
    DISPLAY_NAME = "Video to Audio: MMAudio (Local Comfy)"
    MODEL_TYPE = "audio"
    DESCRIPTION = "Generate audio for video clips through the local ComfyUI MMAudio workflow"

    INPUTS = InputSpec.PROMPT | InputSpec.NEG_PROMPT | InputSpec.VIDEO
    UI_SECTIONS = [
        UISection.PROMPT,
        UISection.NEG_PROMPT,
        UISection.VIDEO_STRIP,
        UISection.AUDIO_DURATION,
        UISection.STEPS,
        UISection.GUIDANCE,
        UISection.SEED,
    ]
    PARAMS = ParamSpec(steps=25, guidance=4.5, audio_length=8.0)
    REQUIRED_PACKAGES = []

    def load(self, prefs, scene, **kw):
        return {
            "gateway": SlopperlyRuntimeGateway(),
            "last_model_card": self.MODEL_ID,
        }

    def generate(self, pipe_obj, inputs: ModelInputs, scene, prefs) -> str:
        if not inputs.video_path or not Path(inputs.video_path).is_file():
            raise ValueError(
                "MMAudio local Comfy workflow requires a selected video strip. "
                "The former image-only and text-only branches remain hidden until "
                "committed local workflow packs pass artifact tests."
            )

        gateway = (pipe_obj or {}).get("gateway") if isinstance(pipe_obj, dict) else None
        if gateway is None:
            gateway = SlopperlyRuntimeGateway()

        self.set_phase(inputs, "Generating audio with local ComfyUI MMAudio")
        filename = solve_path(
            clean_filename(f"{inputs.seed}_{inputs.prompt}_mmaudio") + ".flac"
        )
        return gateway.run_comfy_workflow(
            WORKFLOW_ID,
            inputs,
            scene,
            prefs,
            destination=filename,
        )
