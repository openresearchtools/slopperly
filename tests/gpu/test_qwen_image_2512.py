import json
from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


LOGICAL_NAME = "qwen_image_2512_t2i_gguf"
T2I_WORKFLOW_ID = "qwen_image_2512_t2i_gguf"
I2I_WORKFLOW_ID = "qwen_image_2512_i2i_gguf"


def test_qwen_image_2512_t2i_and_i2i(gpu_cert, plugin_loader, base_models, repo_root):
    t2i = _run_qwen_image_2512_case(
        gpu_cert,
        plugin_loader,
        base_models,
        repo_root,
        workflow_id=T2I_WORKFLOW_ID,
        prompt="a clean product photo of a small ceramic robot on a local workstation",
        seed=251201,
        filename="qwen_image_2512_t2i.png",
        mode="t2i",
    )
    t2i_1328 = _run_qwen_image_2512_case(
        gpu_cert,
        plugin_loader,
        base_models,
        repo_root,
        workflow_id=T2I_WORKFLOW_ID,
        prompt="a clean square Qwen Image 2512 preset validation render",
        seed=251203,
        filename="qwen_image_2512_t2i_1328.png",
        mode="t2i_1328",
        width=1328,
        height=1328,
    )
    i2i = _run_qwen_image_2512_case(
        gpu_cert,
        plugin_loader,
        base_models,
        repo_root,
        workflow_id=I2I_WORKFLOW_ID,
        prompt="turn the source into a polished local Slopperly product photo",
        seed=251202,
        filename="qwen_image_2512_i2i.png",
        mode="i2i",
    )

    manifest_path = gpu_cert.artifact_path(LOGICAL_NAME, "qwen_image_2512_manifest.json")
    manifest = {
        "t2i": t2i,
        "t2i_1328": t2i_1328,
        "i2i": i2i,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    gpu_cert.pass_artifact(
        LOGICAL_NAME,
        manifest_path,
        {
            "kind": "manifest",
            "cases": {
                "t2i": t2i["validation"],
                "t2i_1328": t2i_1328["validation"],
                "i2i": i2i["validation"],
            },
        },
        metadata={
            "runtime_url": t2i["runtime_url"],
            "workflow_packs": {
                "t2i": t2i["workflow_pack"],
                "i2i": i2i["workflow_pack"],
            },
            "artifacts": {
                "t2i": t2i["artifact"],
                "t2i_1328": t2i_1328["artifact"],
                "i2i": i2i["artifact"],
            },
            "source": i2i.get("source", ""),
        },
    )


def _run_qwen_image_2512_case(
    gpu_cert,
    plugin_loader,
    base_models,
    repo_root,
    *,
    workflow_id,
    prompt,
    seed,
    filename,
    mode,
    width=1024,
    height=1024,
):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / workflow_id / "workflow.api.json",
        f"Qwen Image 2512 {mode} Comfy workflow API graph",
    )
    image = None
    source = ""
    input_mode = ""
    strength = 0.5
    if mode == "i2i":
        source_path = gpu_cert.require_file(
            LOGICAL_NAME,
            repo_root / "tests" / "fixtures" / "vsr_source.ppm",
            "Qwen Image 2512 source image fixture",
        )
        image = _load_fixture(gpu_cert, source_path)
        source = str(source_path)
        input_mode = "img2img"
        strength = 0.65

    module = plugin_loader("image", "qwen_image")
    plugin = module.QwenImagePlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, filename)
    module.solve_path = lambda filename: str(output_path)

    inputs = base_models.ModelInputs(
        prompt=prompt,
        neg_prompt="text, watermark, low quality",
        image=image,
        mode=input_mode,
        width=width,
        height=height,
        steps=4,
        guidance=1.0,
        strength=strength,
        seed=seed,
        frames=1,
    )
    prefs = SimpleNamespace(comfyui_url=runtime_url)

    try:
        pipe_obj = plugin.load(prefs, SimpleNamespace())
        with local_only_network():
            result_path = plugin.generate(pipe_obj, inputs, SimpleNamespace(), prefs)
        validation = validate_image(result_path, expected_width=width, expected_height=height)
    except (RuntimeUnavailableError, WorkflowValidationError) as exc:
        gpu_cert.block(LOGICAL_NAME, f"Qwen Image 2512 {mode} Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Qwen Image 2512 {mode} PNG validation failed: {exc}")

    result = {
        "artifact": str(output_path),
        "mode": mode,
        "runtime_url": runtime_url,
        "validation": validation,
        "workflow_pack": str(workflow_pack),
    }
    if source:
        result["source"] = source
    return result


def _load_fixture(gpu_cert, path):
    try:
        from PIL import Image
    except Exception as exc:
        gpu_cert.block(LOGICAL_NAME, f"Pillow is required to load image fixture: {exc}")
    return Image.open(path).convert("RGB")
