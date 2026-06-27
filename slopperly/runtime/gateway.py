"""Dispatch existing ModelPlugin calls to Slopperly local runtimes."""

from __future__ import annotations

from pathlib import Path

from .comfy.workflow_runner import ComfyWorkflowRunner
from .errors import RuntimeUnavailableError, WorkflowValidationError


class SlopperlyRuntimeGateway:
    """Small gateway used by plugins while preserving ModelPlugin.generate()."""

    def __init__(self, package_root: str | Path | None = None):
        self.package_root = Path(package_root) if package_root else Path(__file__).resolve().parents[1]
        self.workflow_root = self.package_root / "workflows" / "comfy"

    def comfy_pack(self, workflow_id: str) -> Path:
        pack = self.workflow_root / workflow_id
        if not pack.is_dir():
            raise RuntimeUnavailableError(
                f"Comfy workflow pack {workflow_id!r} is not committed under "
                f"{self.workflow_root}. This legacy alias is hidden until the "
                "local workflow and artifact test are complete."
            )
        return pack

    def run_comfy_workflow(
        self,
        workflow_id: str,
        inputs,
        scene,
        prefs,
        *,
        destination: str | None = None,
        timeout: float = 3600.0,
    ):
        """Run a committed Comfy workflow pack and return artifact path(s)."""
        pack = self.comfy_pack(workflow_id)
        runner = ComfyWorkflowRunner.from_preferences(prefs)
        try:
            return runner.run_pack(
                pack,
                inputs,
                scene,
                destination=destination,
                timeout=timeout,
            )
        except WorkflowValidationError:
            raise
        except Exception as exc:
            raise RuntimeUnavailableError(
                f"Local Comfy workflow {workflow_id!r} failed: {exc}"
            ) from exc
