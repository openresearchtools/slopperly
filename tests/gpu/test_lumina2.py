from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


LOGICAL_NAME = "lumina2_t2i"
WORKFLOW_ID = "lumina2_t2i"


def test_lumina2_t2i(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / WORKFLOW_ID / "workflow.api.json",
        f"{WORKFLOW_ID} Comfy workflow API graph",
    )

    module = plugin_loader("image", "lumina2")
    plugin = module.Lumina2Plugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "lumina2_t2i.png")
    module.solve_path = lambda generated: str(output_path)

    inputs = base_models.ModelInputs(
        prompt="high quality local Lumina render of a compact workstation, natural light",
        neg_prompt="text, watermark, low quality",
        width=1024,
        height=1024,
        steps=30,
        guidance=4.0,
        seed=510101,
        frames=1,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, SimpleNamespace())
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, SimpleNamespace(), prefs)
        validation = validate_image(result_path, expected_width=1024, expected_height=1024)
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"Lumina2 Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Lumina2 PNG validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "result_path": str(result_path),
            "model_files": {
                "gguf": "lumina_2_model-Q5_K_M.gguf",
                "source_diffusion_bf16": "lumina_2_model_bf16.safetensors",
                "text_encoder": "gemma_2_2b_fp16.safetensors",
                "vae": "lumina2_ae.safetensors",
            },
        },
    )
