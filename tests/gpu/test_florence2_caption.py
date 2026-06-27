import json
from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError
from slopperly.validation.artifacts import ArtifactValidationError, validate_text


LOGICAL_NAME = "florence2_caption_ocr"


def _validate_caption_concepts(logical_name: str, gpu_cert, caption: str) -> dict:
    validation = validate_text(
        caption,
        max_chars=20000,
        forbidden_fragments=["provider error", "connection refused"],
    )
    concept_terms = {
        "red",
        "green",
        "blue",
        "circle",
        "rectangle",
        "block",
        "shape",
        "text",
        "label",
        "slopperly",
        "local",
        "test",
    }
    found = sorted(term for term in concept_terms if term in caption.lower())
    if len(found) < 2:
        gpu_cert.fail(
            logical_name,
            "Florence2 caption did not describe enough known fixture concepts",
            metadata={"caption": caption, "matched_concepts": found},
        )
    validation["matched_concepts"] = found
    return validation


def _validate_ideogram_json(logical_name: str, gpu_cert, text: str) -> tuple[dict, dict]:
    validation = validate_text(
        text,
        max_chars=60000,
        forbidden_fragments=["provider error", "connection refused"],
    )
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        gpu_cert.fail(logical_name, f"Florence2 Ideogram4 output is not JSON: {exc}")
    required = {
        "high_level_description",
        "style_description",
        "light_direction",
        "light_setting",
        "compositional_deconstruction",
    }
    missing = sorted(required - set(data))
    if missing:
        gpu_cert.fail(
            logical_name,
            "Florence2 Ideogram4 JSON is missing required top-level keys",
            metadata={"missing": missing, "keys": sorted(data)},
        )
    elements = data.get("compositional_deconstruction", {}).get("elements", [])
    if not isinstance(elements, list) or not elements:
        gpu_cert.fail(
            logical_name,
            "Florence2 Ideogram4 JSON has no compositional elements",
            metadata={"ideogram4": data},
        )
    ocr_terms = {"slopperly", "local", "test", "text", "label"}
    text_elements = [elem for elem in elements if isinstance(elem, dict) and elem.get("type") == "text"]
    lower_json = text.lower()
    matched_ocr = sorted(term for term in ocr_terms if term in lower_json)
    if not text_elements and not matched_ocr:
        gpu_cert.fail(
            logical_name,
            "Florence2 Ideogram4 JSON did not preserve OCR/text evidence from the fixture",
            metadata={"ideogram4": data},
        )
    validation.update({
        "json_keys": sorted(data),
        "element_count": len(elements),
        "text_element_count": len(text_elements),
        "matched_ocr_terms": matched_ocr,
    })
    return data, validation


def test_florence2_caption_and_ideogram4(gpu_cert, plugin_loader, base_models, repo_root):
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
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        caption_scene = SimpleNamespace(florence2_mode="CAPTION", florence2_send_to_mask=False)
        pipe_obj = plugin.load(prefs, caption_scene)
        caption_inputs = base_models.ModelInputs(
            image=Image.open(image_path).convert("RGB"),
            seed=123,
        )
        with local_only_network():
            caption = plugin.generate(pipe_obj, caption_inputs, caption_scene, prefs)
        caption_validation = _validate_caption_concepts(LOGICAL_NAME, gpu_cert, caption)

        ideogram_scene = SimpleNamespace(florence2_mode="IDEOGRAM4", florence2_send_to_mask=False)
        ideogram_inputs = base_models.ModelInputs(
            image=Image.open(image_path).convert("RGB"),
            seed=456,
        )
        with local_only_network():
            ideogram_text = plugin.generate(pipe_obj, ideogram_inputs, ideogram_scene, prefs)
        ideogram_data, ideogram_validation = _validate_ideogram_json(
            LOGICAL_NAME,
            gpu_cert,
            ideogram_text,
        )
    except RuntimeUnavailableError as exc:
        gpu_cert.block(LOGICAL_NAME, f"Florence2 Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Florence2 text validation failed: {exc}")

    artifact = gpu_cert.artifact_path(LOGICAL_NAME, "caption.txt")
    artifact.write_text(caption, encoding="utf-8")
    ideogram_artifact = gpu_cert.artifact_path(LOGICAL_NAME, "ideogram4.json")
    ideogram_artifact.write_text(json.dumps(ideogram_data, indent=2), encoding="utf-8")
    manifest = gpu_cert.artifact_path(LOGICAL_NAME, "florence2_manifest.json")
    manifest.write_text(
        json.dumps(
            {
                "caption": str(artifact),
                "ideogram4": str(ideogram_artifact),
                "caption_preview": caption[:400],
                "ideogram4_keys": sorted(ideogram_data),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    validation = {
        "caption": caption_validation,
        "ideogram4": ideogram_validation,
    }
    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        manifest,
        validation,
        metadata={
            "runtime_url": runtime_url,
            "source_image": str(image_path),
            "caption_artifact": str(artifact),
            "ideogram4_artifact": str(ideogram_artifact),
        },
    )
