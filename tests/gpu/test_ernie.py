from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


def test_ernie_image_t2i(gpu_cert, plugin_loader, base_models, repo_root):
    _run_ernie_case(
        gpu_cert,
        plugin_loader,
        base_models,
        repo_root,
        logical_name="ernie_image_t2i",
        workflow_id="ernie_image_t2i",
        module_name="ernie",
        class_name="ErniePlugin",
        prompt="high quality local ERNIE render of a compact workstation, natural light",
        negative_prompt="text, watermark, low quality",
        steps=50,
        guidance=4.0,
        seed=310101,
        filename="ernie_image_t2i.png",
        gguf_filename="ernie-image-Q5_K_M.gguf",
    )


def test_ernie_image_turbo_t2i(gpu_cert, plugin_loader, base_models, repo_root):
    _run_ernie_case(
        gpu_cert,
        plugin_loader,
        base_models,
        repo_root,
        logical_name="ernie_image_turbo_t2i",
        workflow_id="ernie_image_turbo_t2i",
        module_name="ernie_turbo",
        class_name="ErnieTurboPlugin",
        prompt="fast local ERNIE Turbo render of a clean product card, crisp lighting",
        negative_prompt="text, watermark, low quality",
        steps=8,
        guidance=1.0,
        seed=320101,
        filename="ernie_image_turbo_t2i.png",
        gguf_filename="ernie-image-turbo-Q5_K_M.gguf",
    )


def _run_ernie_case(
    gpu_cert,
    plugin_loader,
    base_models,
    repo_root,
    *,
    logical_name,
    workflow_id,
    module_name,
    class_name,
    prompt,
    negative_prompt,
    steps,
    guidance,
    seed,
    filename,
    gguf_filename,
):
    gpu_cert.require_cuda(logical_name)
    runtime_url = gpu_cert.require_runtime(logical_name, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        logical_name,
        repo_root / "slopperly" / "workflows" / "comfy" / workflow_id / "workflow.api.json",
        f"{workflow_id} Comfy workflow API graph",
    )

    module = plugin_loader("image", module_name)
    plugin = getattr(module, class_name)()
    output_path = gpu_cert.artifact_path(logical_name, filename)
    module.solve_path = lambda generated: str(output_path)

    inputs = base_models.ModelInputs(
        prompt=prompt,
        neg_prompt=negative_prompt,
        width=1024,
        height=1024,
        steps=steps,
        guidance=guidance,
        seed=seed,
        frames=1,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, SimpleNamespace())
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, SimpleNamespace(), prefs)
        validation = validate_image(result_path, expected_width=1024, expected_height=1024)
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(logical_name, f"ERNIE Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(logical_name, f"ERNIE PNG validation failed: {exc}")

    gpu_cert.pass_artifact(
        logical_name,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "result_path": str(result_path),
            "model_files": {"gguf": gguf_filename},
        },
    )
