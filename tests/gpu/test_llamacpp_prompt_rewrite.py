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
