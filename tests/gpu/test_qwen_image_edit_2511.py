from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


LOGICAL_NAME = "qwen_image_edit_2511_multi_gguf"
WORKFLOW_ID = "qwen_image_edit_2511_multi_gguf"


def test_qwen_image_edit_2511_one_ref(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / WORKFLOW_ID / "workflow.api.json",
        "Qwen Image Edit Comfy workflow API graph",
    )
    first = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "vsr_source.ppm",
        "first Qwen Image Edit reference image fixture",
    )
    image = _load_fixture(gpu_cert, first)

    module = plugin_loader("image", "qwen_image_edit")
    plugin = module.QwenImageEditPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "qwen_image_edit_one_ref.png")
    module.solve_path = lambda filename: str(output_path)

    scene = SimpleNamespace()
    inputs = base_models.ModelInputs(
        prompt="make the reference image warmer with a clean studio background",
        neg_prompt="text, watermark, low quality",
        image=image,
        width=1024,
        height=1024,
        steps=4,
        seed=251101,
        frames=1,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_image(result_path, expected_width=1024, expected_height=1024)
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"Qwen Image Edit one-ref Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Qwen Image Edit one-ref PNG validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "references": [str(first)],
            "mode": "one_ref",
        },
    )


def test_qwen_image_edit_2511_three_ref(
    gpu_cert,
    plugin_loader,
    base_models,
    repo_root,
    sequence_scene_factory,
):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / WORKFLOW_ID / "workflow.api.json",
        "Qwen Image Edit Comfy workflow API graph",
    )
    first = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "vsr_source.ppm",
        "first Qwen Image Edit reference image fixture",
    )
    second = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "birefnet_source.ppm",
        "second Qwen Image Edit reference image fixture",
    )
    third = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "vsr_source.ppm",
        "third Qwen Image Edit reference image fixture",
    )
    image = _load_fixture(gpu_cert, first)

    module = plugin_loader("image", "qwen_image_edit")
    plugin = module.QwenImageEditPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "qwen_image_edit_three_ref.png")
    module.solve_path = lambda filename: str(output_path)

    scene = sequence_scene_factory(
        qwen_strip_1="second",
        qwen_strip_2="third",
        qwen_strip_3="",
    )
    scene.sequence_editor.strips_all.extend([
        SimpleNamespace(name="second", type="IMAGE", filepath=str(second)),
        SimpleNamespace(name="third", type="IMAGE", filepath=str(third)),
    ])
    inputs = base_models.ModelInputs(
        prompt="edit image one using image two for material and image three for composition",
        neg_prompt="text, watermark, low quality",
        image=image,
        width=1024,
        height=1024,
        steps=4,
        seed=251103,
        frames=1,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_image(result_path, expected_width=1024, expected_height=1024)
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"Qwen Image Edit three-ref Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Qwen Image Edit three-ref PNG validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "workflow_pack": str(workflow_pack),
            "references": [str(first), str(second), str(third)],
            "mode": "three_ref",
        },
    )


def _load_fixture(gpu_cert, path):
    try:
        from PIL import Image
    except Exception as exc:
        gpu_cert.block(LOGICAL_NAME, f"Pillow is required to load image fixture: {exc}")
    return Image.open(path).convert("RGB")
