"""Cinematic prompt enhancer via MoviiGen (ZuluVision/MoviiGen1.1_Prompt_Rewriter)."""

from ...models.base import ModelPlugin, InputSpec, UISection, ParamSpec, ModelInputs
from ...utils.helpers import remove_duplicate_phrases
from ...slopperly.runtime.llamacpp.client import (
    DEFAULT_CONTEXT_LENGTH,
    DEFAULT_MAX_NEW_TOKENS,
    LlamaCppClient,
)

_SYSTEM_MSG = (
    "As a cinematic prompt engineer, be creative, rewrite the following into a "
    "comma-separated list of visual details, starting with camera angle, camera "
    "motion and progressing through subject, setting, lighting, atmosphere, style."
)


class MoviiGenRewriterPlugin(ModelPlugin):
    MODEL_ID     = "ZuluVision/MoviiGen1.1_Prompt_Rewriter"
    DISPLAY_NAME = "Prompt Enhancer: MoviiGen"
    MODEL_TYPE   = "text"
    DESCRIPTION  = "MoviiGen Prompt Rewriter"

    INPUTS       = InputSpec.PROMPT   # text-only; no image input
    UI_SECTIONS  = [UISection.PROMPT]
    PARAMS       = ParamSpec()
    REQUIRED_PACKAGES = []

    def load(self, prefs, scene, **kw):
        return {"pipe": None, "last_model_card": self.MODEL_ID}

    def generate(self, pipe, inputs: ModelInputs, scene, prefs) -> str:
        messages = [
            {"role": "system", "content": _SYSTEM_MSG},
            {"role": "user",   "content": inputs.prompt},
        ]
        self.set_phase(inputs, "Generating with llama.cpp")
        client = LlamaCppClient.from_preferences(prefs)
        text, diagnostics = client.chat(
            messages,
            model=getattr(prefs, "llamacpp_text_model", "") or None,
            temperature=float(getattr(inputs, "temperature", 0.7) or 0.7),
            context_length=DEFAULT_CONTEXT_LENGTH,
            max_new_tokens=DEFAULT_MAX_NEW_TOKENS,
        )
        text = remove_duplicate_phrases(text)
        usage = diagnostics.get("usage") or {}
        notes = []
        if usage:
            notes.append(f"llama.cpp usage: {usage}")
        if diagnostics.get("context_fallback"):
            notes.append(str(diagnostics["context_fallback"]))
        if notes:
            inputs.usage_note = "; ".join(notes)
        print("MoviiGen enhanced prompt:", text)
        return text
