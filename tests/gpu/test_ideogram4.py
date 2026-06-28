from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


LOGICAL_NAME = "ideogram4_t2i"
WORKFLOW_ID = "ideogram4_t2i"


def test_ideogram4_t2i(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / WORKFLOW_ID / "workflow.api.json",
        f"{WORKFLOW_ID} Comfy workflow API graph",
    )

    module = plugin_loader("image", "ideogram4")
    plugin = module.Ideogram4Plugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "ideogram4_t2i.png")
    module.solve_path = lambda generated: str(output_path)

    inputs = base_models.ModelInputs(
        prompt="a clean product label reading SLOPPERLY LOCAL, crisp typography, studio lighting",
        width=1024,
        height=1024,
        steps=20,
        guidance=4.0,
        seed=440404,
        frames=1,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)
    scene = SimpleNamespace(ideogram_prompt_upsampling=False)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_image(result_path, expected_width=1024, expected_height=1024)
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"Ideogram 4 Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Ideogram 4 PNG validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "result_path": str(result_path),
            "model_files": {
                "gguf": "ideogram4-transformer-q5_0.gguf",
                "unconditional_gguf": "ideogram4-unconditional_transformer-q5_0.gguf",
                "text_encoder": "qwen3vl_8b_fp8_scaled.safetensors",
                "vae": "flux2-vae.safetensors",
            },
        },
    )
