# Runtime Acceptance Notes

## Required Local Runtime Gates

- ComfyUI must start from Slopperly-owned runtime files.
- Comfy `/object_info` must be reachable.
- Required node classes from `slopperly/runtime/comfy/nodes.lock.yaml` must be present.
- Every `workflow.api.json` must validate as API-format JSON.
- Production generation clients must reject non-local inference URLs.

## Current Evidence

- Python compile check passes for edited production modules.
- Existing backend test passes against `127.0.0.1`.
- Static no-cloud audit passes for production paths.

## Current Blocks

- GPU artifact tests were not run in this block.
- Owned ComfyUI install command currently records the pinned recipe but does not yet clone/install the runtime.
- vLLM, vLLM-Omni, and llama.cpp install/supervisor/client implementations still need full migrations and artifact tests.
