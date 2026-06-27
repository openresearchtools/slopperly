# Runtime Acceptance Notes

## Required Local Runtime Gates

- ComfyUI must start from Slopperly-owned runtime files.
- Comfy `/object_info` must be reachable.
- Required node classes from `slopperly/runtime/comfy/nodes.lock.yaml` must be present.
- Every `workflow.api.json` must validate as API-format JSON.
- Production generation clients must reject non-local inference URLs.
- Production code must not expose or import the old generic remote backend surface.

## Current Evidence

- Python compile check passes for edited production modules.
- Static no-cloud audit passes for production paths.
- Local-only production surface audit passes for remote backend factory/client/UI hooks.
- `python -m slopperly.models.download --dry-run --report-only` plans exact Hugging Face artifact downloads and blocks vague registry entries.
- `python -m slopperly.doctor --local-only --runtimes none --report-only` passes local-only/no-cloud/workflow-pack checks.
- Runtime install commands now have dry-run/report modes that emit `PASS`/`PLAN`/`BLOCKED` evidence before cloning, downloading, or installing packages.

## Current Blocks

- GPU artifact tests were not run in this block.
- Owned ComfyUI install command now has an executable pinned clone/install path for ComfyUI and custom nodes, but the runtime has not been installed or launched in this block.
- vLLM, vLLM-Omni, and llama.cpp install commands now plan or execute their local runtime setup; supervisor launch wiring and artifact tests still need full migration evidence.
- vLLM, vLLM-Omni, and llama.cpp clients now exist with unit coverage, but runtime launch and GPU artifact validation remain blocked until the local model servers are installed and started.
- Artifact validators and workflow/dropdown audits now exist. Dropdown certification remains blocked until real plugin-path GPU artifact evidence is written for each registry entry.
- Add-on preferences now expose local runtime endpoints only; remote backend discovery/API-key generation UI has been removed from production registration. Queue jobs snapshot local runtime endpoints.
- Full doctor with `--cuda --runtimes all` reports CUDA evidence when present and remains BLOCKED for any local runtime server that is not running.
