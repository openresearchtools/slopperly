from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


LOGICAL_NAME = "nucleus_image_t2i"
WORKFLOW_ID = "nucleus_image_t2i"


def test_nucleus_image_t2i(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / WORKFLOW_ID / "workflow.api.json",
        f"{WORKFLOW_ID} Comfy workflow API graph",
    )

    module = plugin_loader("image", "nucleus_moe")
    plugin = module.NucleusMoEPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "nucleus_image_t2i.png")
    module.solve_path = lambda generated: str(output_path)

    inputs = base_models.ModelInputs(
        prompt="high quality local Nucleus Image render of a compact workstation, natural light",
        neg_prompt="text, watermark, low quality",
        width=1024,
        height=1024,
        steps=20,
        guidance=8.0,
        seed=530101,
        frames=1,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, SimpleNamespace())
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, SimpleNamespace(), prefs)
        validation = validate_image(result_path, expected_width=1024, expected_height=1024)
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"Nucleus Image Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Nucleus Image PNG validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "result_path": str(result_path),
            "offload_strategy": "sequential_cpu_preferred",
            "model_files": {
                "base_snapshot": getattr(inputs, "nucleus_model_path", ""),
                "fp8_patch": getattr(inputs, "nucleus_fp8_patch_path", ""),
                "fp8_weights": getattr(inputs, "nucleus_fp8_weights_path", ""),
            },
        },
    )
