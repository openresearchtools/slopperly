import importlib
import importlib.util
import os
import re
import sys
import tempfile
import types
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from slopperly.audit.network_guard import local_only_network
from slopperly.config.registry import load_runtimes_config
from slopperly.validation.certification import (
    BLOCKED,
    FAIL,
    PASS,
    write_certification_record,
)

TEST_PACKAGE = "slopperly_gpu_plugin_test"


def pytest_addoption(parser):
    parser.addoption("--device", default="cuda", help="GPU device profile, normally cuda")
    parser.addoption("--profile", default="smoke_16gb", help="Slopperly certification profile")
    parser.addoption(
        "--runtime-timeout",
        type=float,
        default=5.0,
        help="Seconds to wait for local runtime health probes",
    )


@pytest.fixture(scope="session")
def repo_root():
    return ROOT


@pytest.fixture(scope="session")
def base_models():
    install_plugin_import_harness(ROOT)
    return sys.modules[f"{TEST_PACKAGE}.models.base"]


@pytest.fixture(scope="session")
def plugin_loader():
    install_plugin_import_harness(ROOT)

    def _load(kind: str, filename: str):
        return load_plugin_module(ROOT, kind, filename)

    return _load


@pytest.fixture
def gpu_cert(request):
    return GpuCertificationContext(request)


@pytest.fixture
def sequence_scene_factory():
    return fake_sequence_scene


class GpuCertificationContext:
    def __init__(self, request):
        self.request = request
        self.root = ROOT
        self.profile = request.config.getoption("--profile")
        self.device = request.config.getoption("--device")
        self.timeout = float(request.config.getoption("--runtime-timeout"))

    @property
    def command(self) -> str:
        return f"pytest {self.request.node.nodeid} --device {self.device} --profile {self.profile}"

    def require_cuda(self, logical_name: str) -> None:
        if self.device != "cuda":
            self.block(logical_name, f"GPU artifact tests require --device cuda, got {self.device!r}")

    def runtime_url(self, runtime: str) -> str:
        env_name = {
            "comfyui": "SLOPPERLY_COMFYUI_URL",
            "vllm": "SLOPPERLY_VLLM_URL",
            "vllm_omni": "SLOPPERLY_VLLM_OMNI_URL",
            "llamacpp": "SLOPPERLY_LLAMACPP_URL",
        }[runtime]
        if os.environ.get(env_name):
            return os.environ[env_name]
        config = load_runtimes_config(self.root).get(runtime, {})
        host = config.get("host", "127.0.0.1")
        port = config.get("port")
        return f"http://{host}:{port}"

    def require_runtime(self, logical_name: str, runtime: str, paths=("/health", "/v1/models")) -> str:
        url = self.runtime_url(runtime).rstrip("/")
        errors: list[str] = []
        for path in paths:
            try:
                with local_only_network():
                    with urllib.request.urlopen(url + path, timeout=self.timeout) as response:
                        if 200 <= response.status < 500:
                            return url
                        errors.append(f"{path}: HTTP {response.status}")
            except (OSError, urllib.error.URLError) as exc:
                errors.append(f"{path}: {exc}")
        self.block(
            logical_name,
            f"{runtime} local runtime is not reachable at {url}; "
            f"health probe errors: {'; '.join(errors)}",
            metadata={"runtime": runtime, "url": url, "health_paths": list(paths)},
        )
        return url

    def require_file(self, logical_name: str, path: Path, description: str) -> Path:
        if not path.is_file():
            self.block(logical_name, f"required {description} is missing: {path}")
        return path

    def artifact_path(self, logical_name: str, filename: str) -> Path:
        path = self.root / ".slopperly" / "gpu-artifacts" / self.profile / logical_name / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def pass_artifact(self, logical_name: str, artifact: Path, validation: dict, metadata: dict | None = None):
        write_certification_record(
            root=self.root,
            profile=self.profile,
            logical_name=logical_name,
            status=PASS,
            command=self.command,
            artifact=str(artifact),
            validation=validation,
            metadata=metadata or {},
        )

    def block(self, logical_name: str, reason: str, metadata: dict | None = None):
        write_certification_record(
            root=self.root,
            profile=self.profile,
            logical_name=logical_name,
            status=BLOCKED,
            command=self.command,
            reason=reason,
            metadata=metadata or {},
        )
        pytest.fail(f"BLOCKED {logical_name}: {reason}")

    def fail(self, logical_name: str, reason: str, metadata: dict | None = None):
        write_certification_record(
            root=self.root,
            profile=self.profile,
            logical_name=logical_name,
            status=FAIL,
            command=self.command,
            reason=reason,
            metadata=metadata or {},
        )
        pytest.fail(f"FAIL {logical_name}: {reason}")


class FakeStrips:
    def __init__(self, editor):
        self.editor = editor

    def new_effect(self, **kwargs):
        strip = SimpleNamespace(**kwargs)
        strip.location = [0.0, 0.0]
        strip.text = ""
        strip.frame_final_start = kwargs["frame_start"]
        strip.frame_final_duration = kwargs["length"]
        strip.channel = kwargs["channel"]
        strip.type = kwargs["type"]
        strip.right_handle = kwargs["frame_start"] + kwargs["length"]
        self.editor.created.append(strip)
        self.editor.strips_all.append(strip)
        return strip


class FakeSeqEditor:
    def __init__(self):
        self.created = []
        self.strips_all = []
        self.active_strip = None
        self.strips = FakeStrips(self)


def fake_sequence_scene(**kwargs):
    scene = SimpleNamespace(
        sequence_editor=FakeSeqEditor(),
        render=SimpleNamespace(fps=24, fps_base=1),
    )
    for key, value in kwargs.items():
        setattr(scene, key, value)
    return scene


def _find_strip_by_name(scene, name):
    editor = getattr(scene, "sequence_editor", None)
    strips = getattr(editor, "strips", None)
    if not isinstance(strips, list):
        strips = getattr(editor, "strips_all", [])
    for strip in strips or []:
        if getattr(strip, "name", "") == name:
            return strip
    return None


def _get_strip_path(strip):
    return getattr(strip, "filepath", None) or getattr(strip, "path", None)


def install_plugin_import_harness(root: Path) -> None:
    _ensure_package(TEST_PACKAGE)
    _ensure_package(f"{TEST_PACKAGE}.models")
    _ensure_package(f"{TEST_PACKAGE}.models_plugins")
    _ensure_package(f"{TEST_PACKAGE}.models_plugins.text")
    _ensure_package(f"{TEST_PACKAGE}.models_plugins.audio")
    _ensure_package(f"{TEST_PACKAGE}.models_plugins.image")
    _ensure_package(f"{TEST_PACKAGE}.models_plugins.video")
    _ensure_package(f"{TEST_PACKAGE}.utils")

    if f"{TEST_PACKAGE}.models.base" not in sys.modules:
        _load_module(f"{TEST_PACKAGE}.models.base", root / "models/base.py")

    helpers = types.ModuleType(f"{TEST_PACKAGE}.utils.helpers")
    helpers.clean_filename = lambda value: re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_")
    helpers.solve_path = lambda filename: str(Path(tempfile.gettempdir()) / filename)
    helpers.remove_duplicate_phrases = lambda text: text
    helpers.find_strip_by_name = _find_strip_by_name
    helpers.get_strip_path = _get_strip_path
    sys.modules[f"{TEST_PACKAGE}.utils.helpers"] = helpers

    for name in [
        "slopperly",
        "slopperly.runtime",
        "slopperly.runtime.gateway",
        "slopperly.runtime.comfy",
        "slopperly.runtime.comfy.api_client",
        "slopperly.runtime.comfy.workflow_runner",
        "slopperly.runtime.llamacpp",
        "slopperly.runtime.llamacpp.client",
        "slopperly.runtime.vllm",
        "slopperly.runtime.vllm.stt_client",
        "slopperly.runtime.vllm.vlm_client",
        "slopperly.runtime.vllm_omni",
        "slopperly.runtime.vllm_omni.tts_client",
    ]:
        sys.modules[f"{TEST_PACKAGE}.{name}"] = importlib.import_module(name)


def load_plugin_module(root: Path, kind: str, filename: str):
    module_name = f"{TEST_PACKAGE}.models_plugins.{kind}.{filename}"
    return _load_module(module_name, root / "models_plugins" / kind / f"{filename}.py")


def _ensure_package(name: str) -> types.ModuleType:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = []
        sys.modules[name] = module
    return module


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module
