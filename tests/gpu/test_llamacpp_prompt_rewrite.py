from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError
from slopperly.validation.artifacts import ArtifactValidationError, validate_text


LOGICAL_NAME = "llamacpp_prompt_rewriter"


def test_llamacpp_prompt_rewrite(gpu_cert, plugin_loader, base_models):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "llamacpp")
    module = plugin_loader("text", "moviigen_rewriter")
    plugin = module.MoviiGenRewriterPlugin()
    inputs = base_models.ModelInputs(
        prompt="a quiet train station at midnight with one service robot",
        temperature=0.7,
    )
    prefs = SimpleNamespace(llamacpp_url=runtime_url, llamacpp_text_model="")

    try:
        pipe_obj = plugin.load(prefs, SimpleNamespace())
        with local_only_network():
            result = plugin.generate(pipe_obj, inputs, SimpleNamespace(), prefs)
        validation = validate_text(
            result,
            max_chars=20000,
            forbidden_fragments=["provider error", "connection refused"],
        )
        lowered = result.lower()
        missing = [term for term in ["train", "station", "robot"] if term not in lowered]
        if missing:
            raise ArtifactValidationError(
                f"llama.cpp rewrite dropped expected prompt concepts {missing}: {result!r}"
            )
        validation["expected_concepts"] = ["train", "station", "robot"]
        usage_note = getattr(inputs, "usage_note", "")
        if "n_ctx=32768" not in usage_note:
            raise ArtifactValidationError(
                f"llama.cpp context fallback diagnostic missing from usage_note: {usage_note!r}"
            )
        validation["context_fallback_recorded"] = True
    except RuntimeUnavailableError as exc:
        gpu_cert.block(LOGICAL_NAME, f"llama.cpp plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"llama.cpp text validation failed: {exc}")

    artifact = gpu_cert.artifact_path(LOGICAL_NAME, "prompt_rewrite.txt")
    artifact.write_text(result, encoding="utf-8")
    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        artifact,
        validation,
        metadata={"runtime_url": runtime_url, "usage_note": getattr(inputs, "usage_note", "")},
    )
