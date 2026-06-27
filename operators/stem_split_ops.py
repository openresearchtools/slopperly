"""Stem splitter operator backed by the local Comfy Demucs plugin path."""

import json
import threading
from types import SimpleNamespace

import bpy
from bpy.types import Operator

from ..models.base import ModelInputs
from ..models_plugins.audio.stem_split import StemSplitterPlugin, _MULTI_STEM_PREFIX
from ..utils.helpers import ADDON_ID, find_first_empty_channel, render_strip_to_wav

STEM_NAMES_4 = ["vocals", "drums", "bass", "other"]
STEM_NAMES_6 = ["vocals", "drums", "bass", "other", "guitar", "piano"]

_state = {
    "running": False,
    "phase": "",
    "progress": 0.0,
    "stem_paths": None,
    "error": None,
}


def _insert_stem_paths(ctx, stem_paths):
    scene       = ctx["scene"]
    frame_start = ctx["frame_start"]
    frame_end   = ctx["frame_end"]
    src_channel = ctx["src_channel"]
    strip_name  = ctx["strip_name"]
    selected    = ctx["selected"]

    next_min_ch = src_channel + 1
    ed = scene.sequence_editor

    for stem_name in selected:
        out_path = stem_paths.get(stem_name)
        if not out_path:
            print(f"[Stem Splitter] Missing local Comfy output for '{stem_name}'")
            continue

        ch = find_first_empty_channel(frame_start, frame_end)
        ch = max(ch, next_min_ch)
        next_min_ch = ch + 1

        ed.strips.new_sound(
            name=f"{stem_name} | {strip_name}",
            filepath=out_path,
            channel=ch,
            frame_start=frame_start,
        )
        print(f"[Stem Splitter] Inserted '{stem_name}' on channel {ch}: {out_path}")

    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == "SEQUENCE_EDITOR":
                area.tag_redraw()


class SEQUENCER_OT_stem_split(Operator):
    """Separate the active audio/video strip into individual stems via local ComfyUI"""

    bl_idname  = "sequencer.stem_split"
    bl_label   = "Split Stems"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return (
            not _state["running"]
            and context.scene.sequence_editor is not None
            and context.scene.sequence_editor.active_strip is not None
            and context.scene.sequence_editor.active_strip.type in ("SOUND", "MOVIE")
        )

    def invoke(self, context, event):
        scene   = context.scene
        model   = scene.stem_split_model
        if model == "htdemucs_6s":
            self.report(
                {"ERROR"},
                "Six-stem splitting is blocked until a pinned local Comfy workflow is certified.",
            )
            return {"CANCELLED"}
        all_stems = STEM_NAMES_6 if model == "htdemucs_6s" else STEM_NAMES_4
        selected  = [s for s in all_stems if getattr(scene, f"stem_split_{s}")]
        if not selected:
            self.report({"ERROR"}, "Select at least one stem")
            return {"CANCELLED"}
        return self.execute(context)

    def execute(self, context):
        scene   = context.scene
        strip   = scene.sequence_editor.active_strip
        model   = scene.stem_split_model
        if model == "htdemucs_6s":
            self.report(
                {"ERROR"},
                "Six-stem splitting is blocked until a pinned local Comfy workflow is certified.",
            )
            return {"CANCELLED"}
        all_stems = STEM_NAMES_6 if model == "htdemucs_6s" else STEM_NAMES_4
        selected  = [s for s in all_stems if getattr(scene, f"stem_split_{s}")]

        _state.update(running=True, phase="Rendering strip to WAV...", progress=0.0,
                      stem_paths=None, error=None)

        # Pre-render on main thread: handles trimming, effects, any format.
        audio_path = render_strip_to_wav(context, strip)
        if not audio_path:
            _state["running"] = False
            self.report({"ERROR"}, "Failed to render strip audio to WAV")
            return {"CANCELLED"}

        frame_start = strip.frame_final_start
        frame_end   = strip.frame_final_start + strip.frame_final_duration
        src_channel = strip.channel
        strip_name  = strip.name

        _ctx = {
            "scene":       scene,
            "audio_path":  audio_path,
            "frame_start": frame_start,
            "frame_end":   frame_end,
            "src_channel": src_channel,
            "strip_name":  strip_name,
            "selected":    selected,
        }
        scene_snapshot = SimpleNamespace(
            stem_split_model=model,
            stem_split_vocals=getattr(scene, "stem_split_vocals", True),
            stem_split_drums=getattr(scene, "stem_split_drums", True),
            stem_split_bass=getattr(scene, "stem_split_bass", True),
            stem_split_other=getattr(scene, "stem_split_other", True),
            stem_split_guitar=getattr(scene, "stem_split_guitar", False),
            stem_split_piano=getattr(scene, "stem_split_piano", False),
            stem_split_chunk_fade_shape=getattr(scene, "stem_split_chunk_fade_shape", "linear"),
            stem_split_chunk_length=getattr(scene, "stem_split_chunk_length", 10.0),
            stem_split_chunk_overlap=getattr(scene, "stem_split_chunk_overlap", 0.1),
        )
        addon_prefs = context.preferences.addons[ADDON_ID].preferences
        prefs_snapshot = SimpleNamespace(
            comfyui_url=getattr(addon_prefs, "comfyui_url", "http://127.0.0.1:8188"),
            comfyui_timeout=getattr(addon_prefs, "comfyui_timeout", 3600.0),
        )

        context.window_manager.progress_begin(0, 100)

        def _worker():
            try:
                def _progress(step, total):
                    _state["progress"] = (float(step) / float(total)) if total else 0.0

                def _phase(label):
                    _state["phase"] = label

                inputs = ModelInputs(
                    audio_ref=audio_path,
                    progress_fn=_progress,
                    phase_fn=_phase,
                )
                inputs.output_basename = strip_name
                plugin = StemSplitterPlugin()
                pipe_obj = plugin.load(prefs_snapshot, scene_snapshot)
                result = plugin.generate(pipe_obj, inputs, scene_snapshot, prefs_snapshot)
                if not result.startswith(_MULTI_STEM_PREFIX):
                    raise RuntimeError(
                        "Local Comfy stem splitter returned an unexpected result shape."
                    )
                _state["stem_paths"] = json.loads(result[len(_MULTI_STEM_PREFIX):])
                _state["progress"] = 1.0

            except Exception as exc:
                import traceback
                _state["error"] = f"{exc}\n{traceback.format_exc()}"
            finally:
                _state["running"] = False

        threading.Thread(target=_worker, daemon=True).start()

        def _tick():
            try:
                wm = bpy.context.window_manager
                wm.progress_update(int(_state["progress"] * 100))

                if _state["running"]:
                    for win in wm.windows:
                        for area in win.screen.areas:
                            if area.type == "SEQUENCE_EDITOR":
                                area.tag_redraw()
                    return 0.2

                wm.progress_end()

                if _state["error"]:
                    print(f"[Stem Splitter] Error:\n{_state['error']}")
                    return None

                _insert_stem_paths(_ctx, _state["stem_paths"] or {})
            except Exception as exc:
                print(f"[Stem Splitter] Timer error: {exc}")
            return None

        bpy.app.timers.register(_tick, first_interval=0.2)
        return {"FINISHED"}
