from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


LOGICAL_NAME = "qwen_image_2512_t2i_gguf"
T2I_WORKFLOW_ID = "qwen_image_2512_t2i_gguf"
I2I_WORKFLOW_ID = "qwen_image_2512_i2i_gguf"


def test_qwen_image_2512_t2i(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / T2I_WORKFLOW_ID / "workflow.api.json",
        "Qwen Image 2512 text-to-image Comfy workflow API graph",
    )

    module = plugin_loader("image", "qwen_image")
    plugin = module.QwenImagePlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "qwen_image_2512_t2i.png")
    module.solve_path = lambda filename: str(output_path)

    inputs = base_models.ModelInputs(
        prompt="a clean product photo of a small ceramic robot on a local workstation",
        neg_prompt="text, watermark, low quality",
        width=1024,
        height=1024,
        steps=4,
        guidance=1.0,
        seed=251201,
        frames=1,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, SimpleNamespace())
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, SimpleNamespace(), prefs)
        validation = validate_image(result_path, expected_width=1024, expected_height=1024)
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"Qwen Image 2512 T2I Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Qwen Image 2512 T2I PNG validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "mode": "t2i",
        },
    )


def test_qwen_image_2512_i2i(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / I2I_WORKFLOW_ID / "workflow.api.json",
        "Qwen Image 2512 image-to-image Comfy workflow API graph",
    )
    source = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "vsr_source.ppm",
        "Qwen Image 2512 source image fixture",
    )
    image = _load_fixture(gpu_cert, source)

    module = plugin_loader("image", "qwen_image")
    plugin = module.QwenImagePlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "qwen_image_2512_i2i.png")
    module.solve_path = lambda filename: str(output_path)

    inputs = base_models.ModelInputs(
        prompt="turn the source into a polished local Slopperly product photo",
        neg_prompt="text, watermark, low quality",
        image=image,
        mode="img2img",
        width=1024,
        height=1024,
        steps=4,
        guidance=1.0,
        strength=0.65,
        seed=251202,
        frames=1,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, SimpleNamespace())
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, SimpleNamespace(), prefs)
        validation = validate_image(result_path, expected_width=1024, expected_height=1024)
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"Qwen Image 2512 I2I Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Qwen Image 2512 I2I PNG validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "source": str(source),
            "mode": "i2i",
        },
    )


def _load_fixture(gpu_cert, path):
    try:
        from PIL import Image
    except Exception as exc:
        gpu_cert.block(LOGICAL_NAME, f"Pillow is required to load image fixture: {exc}")
    return Image.open(path).convert("RGB")
