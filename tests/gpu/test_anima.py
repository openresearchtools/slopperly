import json
from types import SimpleNamespace

from slopperly.audit.network_guard import local_only_network
from slopperly.runtime.errors import RuntimeUnavailableError, WorkflowValidationError
from slopperly.validation.artifacts import ArtifactValidationError, validate_image


LOGICAL_NAME = "anima_t2i_i2i"


def test_anima_t2i_and_i2i(gpu_cert, plugin_loader, base_models, repo_root):
    t2i = _run_anima_case(
        gpu_cert,
        plugin_loader,
        base_models,
        repo_root,
        workflow_id="anima_t2i_i2i",
        prompt="anime portrait of a small local runtime console, clean cel shading",
        seed=240101,
        filename="anima_t2i.png",
        mode="txt2img",
    )
    i2i = _run_anima_case(
        gpu_cert,
        plugin_loader,
        base_models,
        repo_root,
        workflow_id="anima_t2i_i2i_img2img",
        prompt="polish the source into an Anima anime-style local render",
        seed=240102,
        filename="anima_i2i.png",
        mode="img2img",
    )

    manifest_path = gpu_cert.artifact_path(LOGICAL_NAME, "anima_manifest.json")
    manifest = {
        "t2i": t2i,
        "img2img": i2i,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    gpu_cert.pass_artifact(
        LOGICAL_NAME,
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
            "artifacts": {
                "t2i": t2i["artifact"],
                "img2img": i2i["artifact"],
            },
            "source": i2i.get("source"),
        },
    )


def _run_anima_case(
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
):
    gpu_cert.require_cuda(LOGICAL_NAME)
    runtime_url = gpu_cert.require_runtime(LOGICAL_NAME, "comfyui", paths=("/object_info",))
    workflow_pack = gpu_cert.require_file(
        LOGICAL_NAME,
        repo_root / "slopperly" / "workflows" / "comfy" / workflow_id / "workflow.api.json",
        f"{workflow_id} Comfy workflow API graph",
    )
    image = None
    source = None
    if mode == "img2img":
        source = gpu_cert.require_file(
            LOGICAL_NAME,
            repo_root / "tests" / "fixtures" / "vsr_source.ppm",
            "Anima source image fixture",
        )
        image = _load_fixture(gpu_cert, source)

    module = plugin_loader("image", "anima")
    plugin = module.AnimaPlugin()
    output_path = gpu_cert.artifact_path(LOGICAL_NAME, filename)
    module.solve_path = lambda generated: str(output_path)

    inputs = base_models.ModelInputs(
        prompt=prompt,
        neg_prompt="text, watermark, low quality, blurry",
        image=image,
        mode=mode,
        width=1024,
        height=1024,
        steps=25,
        guidance=4.0,
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
        gpu_cert.block(LOGICAL_NAME, f"Anima Comfy plugin path runtime error: {exc}")
    except ArtifactValidationError as exc:
        gpu_cert.fail(LOGICAL_NAME, f"Anima PNG validation failed: {exc}")

    metadata = {
        "runtime_url": runtime_url,
        "workflow_pack": str(workflow_pack),
        "mode": mode,
        "artifact": str(output_path),
        "result_path": str(result_path),
        "validation": validation,
    }
    if source is not None:
        metadata["source"] = str(source)
    return metadata


def _load_fixture(gpu_cert, path):
    try:
        from PIL import Image
    except Exception as exc:
        gpu_cert.block(LOGICAL_NAME, f"Pillow is required to load image fixture: {exc}")
    return Image.open(path).convert("RGB")
