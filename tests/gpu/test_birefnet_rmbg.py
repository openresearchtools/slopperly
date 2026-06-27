from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


LOGICAL_NAME = "birefnet_rmbg"


def test_birefnet_rmbg(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    image_path = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "birefnet_source.ppm",
        "BiRefNet source image fixture",
    )
    try:
        from PIL import Image
    except Exception as exc:
        gpu_cert.block(LOGICAL_NAME, f"Pillow is required to load image fixture: {exc}")

    module = plugin_loader("image", "birefnet")
    plugin = module.BiRefNetPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, "birefnet_rmbg.png")
    module.solve_path = lambda filename: str(output_path)

    source = Image.open(image_path).convert("RGB")
    scene = SimpleNamespace()
    inputs = base_models.ModelInputs(
        image=source.copy(),
        seed=123,
        frames=1,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_image(
            result_path,
            expected_width=source.width,
            expected_height=source.height,
            require_alpha=True,
        )
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"BiRefNet Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"BiRefNet PNG alpha validation failed: {exc}")

    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        output_path,
        validation,
        metadata={"runtime_url": runtime_url, "source_image": str(image_path)},
    )
