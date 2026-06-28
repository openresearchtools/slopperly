from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


LOGICAL_NAME = "flux_redux_restyle"
WORKFLOW_ID = "flux_redux_restyle"


def test_flux_redux_restyle(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / WORKFLOW_ID / "workflow.api.json",
        f"{WORKFLOW_ID} Comfy workflow API graph",
    )
    source = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "vsr_source.ppm",
        "FLUX Redux source image fixture",
    )

    module = plugin_loader("image", "flux_redux")
    plugin = module.FluxReduxPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "flux_redux_restyle.png")
    module.solve_path = lambda generated: str(output_path)

    inputs = base_models.ModelInputs(
        image=str(source),
        width=1024,
        height=1024,
        steps=25,
        guidance=3.5,
        seed=620101,
        frames=1,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, SimpleNamespace())
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, SimpleNamespace(), prefs)
        validation = validate_image(result_path, expected_width=1024, expected_height=1024)
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"FLUX Redux Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"FLUX Redux PNG validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "result_path": str(result_path),
            "source": str(source),
            "model_files": {
                "gguf": "flux1-dev-Q5_K_M.gguf",
                "style_model": "flux1-redux-dev.safetensors",
                "clip_vision": "sigclip_vision_patch14_384.safetensors",
            },
        },
    )
