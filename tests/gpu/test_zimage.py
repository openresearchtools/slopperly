import json
from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


BASE_LOGICAL_NAME = "zimage_t2i_i2i"
TURBO_LOGICAL_NAME = "zimage_turbo_t2i_i2i"


def test_zimage_base_t2i_and_i2i(gpu_cert, plugin_loader, base_models, repo_root):
    t2i = _run_zimage_case(
        gpu_cert,
        plugin_loader,
        base_models,
        repo_root,
        logical_name=BASE_LOGICAL_NAME,
        workflow_id="zimage_t2i_i2i",
        plugin_class="ZImagePlugin",
        prompt="a clean Z-Image product photo of a small local runtime console",
        steps=30,
        guidance=7.0,
        seed=120101,
        filename="zimage_t2i.png",
        mode="txt2img",
    )
    i2i = _run_zimage_case(
        gpu_cert,
        plugin_loader,
        base_models,
        repo_root,
        logical_name=BASE_LOGICAL_NAME,
        workflow_id="zimage_t2i_i2i_img2img",
        plugin_class="ZImagePlugin",
        prompt="polish the source into a clean Z-Image local product render",
        steps=30,
        guidance=7.0,
        seed=120102,
        filename="zimage_i2i.png",
        mode="img2img",
    )

    manifest_path = gpu_cert.artifact_path(BASE_LOGICAL_NAME, "zimage_manifest.json")
    manifest = {
        "t2i": t2i,
        "img2img": i2i,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    gpu_cert.pass_artifact(
        BASE_LOGICAL_NAME,
        manifest_path,
        {
            "kind": "manifest",
            "cases": {
                "t2i": t2i["validation"],
                "img2img": i2i["validation"],
            },
        },
        metadata={
            "runtime_url": t2i["runtime_url"],
            "workflow_packs": {
                "t2i": t2i["workflow_pack"],
                "img2img": i2i["workflow_pack"],
            },
            "model_files": {
                "gguf": "z-image-Q5_K_M.gguf",
                "text_encoder": "qwen_3_4b.safetensors",
                "vae": "ae.safetensors",
            },
            "artifacts": {
                "t2i": t2i["artifact"],
                "img2img": i2i["artifact"],
            },
            "source": i2i.get("source", ""),
        },
    )


def test_zimage_turbo_t2i_and_i2i(gpu_cert, plugin_loader, base_models, repo_root):
    t2i = _run_zimage_case(
        gpu_cert,
        plugin_loader,
        base_models,
        repo_root,
        logical_name=TURBO_LOGICAL_NAME,
        workflow_id="zimage_turbo_t2i_i2i",
        plugin_class="ZImageTurboPlugin",
        prompt="a fast Z-Image Turbo product photo of a local runtime console",
        steps=8,
        guidance=0.0,
        seed=130101,
        filename="zimage_turbo_t2i.png",
        mode="txt2img",
    )
    i2i = _run_zimage_case(
        gpu_cert,
        plugin_loader,
        base_models,
        repo_root,
        logical_name=TURBO_LOGICAL_NAME,
        workflow_id="zimage_turbo_t2i_i2i_img2img",
        plugin_class="ZImageTurboPlugin",
        prompt="polish the source into a fast Z-Image Turbo local product render",
        steps=8,
        guidance=0.0,
        seed=130102,
        filename="zimage_turbo_i2i.png",
        mode="img2img",
    )

    manifest_path = gpu_cert.artifact_path(TURBO_LOGICAL_NAME, "zimage_turbo_manifest.json")
    manifest = {
        "t2i": t2i,
        "img2img": i2i,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    gpu_cert.pass_artifact(
        TURBO_LOGICAL_NAME,
        manifest_path,
        {
            "kind": "manifest",
            "cases": {
                "t2i": t2i["validation"],
                "img2img": i2i["validation"],
            },
        },
        metadata={
            "runtime_url": t2i["runtime_url"],
            "workflow_packs": {
                "t2i": t2i["workflow_pack"],
                "img2img": i2i["workflow_pack"],
            },
            "model_files": {
                "gguf": "z-image-turbo-Q5_K_M.gguf",
                "text_encoder": "qwen_3_4b.safetensors",
                "vae": "ae.safetensors",
            },
            "artifacts": {
                "t2i": t2i["artifact"],
                "img2img": i2i["artifact"],
            },
            "source": i2i.get("source", ""),
        },
    )


def _run_zimage_case(
    gpu_cert,
    plugin_loader,
    base_models,
    repo_root,
    *,
    logical_name,
    workflow_id,
    plugin_class,
    prompt,
    steps,
    guidance,
    seed,
    filename,
    mode,
):
    gpu_cert.require_cuda(logical_name)
    runtime_url = gpu_cert.require_runtime(logical_name, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        logical_name,
        repo_root / "slopperly" / "workflows" / "comfy" / workflow_id / "workflow.api.json",
        f"{workflow_id} Comfy workflow API graph",
    )
    image = None
    source = None
    if mode == "img2img":
        source = gpu_cert.require_file(
            logical_name,
            repo_root / "tests" / "fixtures" / "vsr_source.ppm",
            "Z-Image source image fixture",
        )
        image = _load_fixture(gpu_cert, logical_name, source)

    module = plugin_loader("image", "zimage")
    plugin = getattr(module, plugin_class)()
    output_path = gpu_cert.artifact_path(logical_name, filename)
    module.solve_path = lambda generated: str(output_path)

    inputs = base_models.ModelInputs(
        prompt=prompt,
        neg_prompt="text, watermark, low quality",
        image=image,
        mode=mode,
        width=1024,
        height=1024,
        steps=steps,
        guidance=guidance,
        strength=0.65,
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
        gpu_cert.block(logical_name, f"{plugin_class} Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(logical_name, f"{plugin_class} PNG validation failed: {exc}")

    result = {
        "artifact": str(output_path),
        "validation": validation,
        "runtime_url": runtime_url,
        "workflow_pack": str(workflow_pack),
        "mode": mode,
    }
    if source is not None:
        result["source"] = str(source)
    return result


def _load_fixture(gpu_cert, logical_name, path):
    try:
        from PIL import Image
    except Exception as exc:
        gpu_cert.block(logical_name, f"Pillow is required to load image fixture: {exc}")
    return Image.open(path).convert("RGB")
