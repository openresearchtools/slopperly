from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError
from slopperly.validation.artifacts import ArtifactValidationError, validate_text


LOGICAL_NAME = "florence2_caption_ocr"


def test_florence2_caption(gpu_cert, plugin_loader, base_models, repo_root):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    image_path = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "tests" / "fixtures" / "florence2_caption.png",
        "Florence2 caption image fixture",
    )
    try:
        from PIL import Image
    except Exception as exc:
        gpu_cert.block(LOGICAL_NAME, f"Pillow is required to load image fixture: {exc}")

    module = plugin_loader("text", "florence2")
    plugin = module.Florence2Plugin()
    scene = SimpleNamespace(florence2_mode="CAPTION", florence2_send_to_mask=False)
    inputs = base_models.ModelInputs(
        image=Image.open(image_path).convert("RGB"),
        seed=123,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, scene)
        with local_only_network():
            result = plugin.generate(pipe_obj, inputs, scene, prefs)
        validation = validate_text(
            result,
            max_chars=20000,
            forbidden_fragments=["provider error", "connection refused"],
        )
    except RuntimeUnavailableError as exc:
        gpu_cert.block(LOGICAL_NAME, f"Florence2 Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Florence2 caption validation failed: {exc}")

    artifact = gpu_cert.artifact_path(LOGICAL_NAME, "caption.txt")
    artifact.write_text(result, encoding="utf-8")
    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        artifact,
        validation,
        metadata={"runtime_url": runtime_url, "source_image": str(image_path)},
    )
