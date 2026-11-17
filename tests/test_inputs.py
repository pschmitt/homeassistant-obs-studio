"""Tests for the audio input helpers, run against a fake obs-websocket client.

The package ``__init__`` imports Home Assistant, so the pure modules are loaded
through a stub package that only provides ``__path__``.
"""

from __future__ import annotations

import math
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

_PKG = Path(__file__).resolve().parent.parent / "custom_components" / "obs_studio"
_stub = types.ModuleType("obs_pure")
_stub.__path__ = [str(_PKG)]
sys.modules.setdefault("obs_pure", _stub)

from obs_pure.exceptions import OBSInputError  # noqa: E402
from obs_pure.inputs import (  # noqa: E402
    InputTarget,
    next_volume,
    resolve_inputs,
    set_mute,
    step_volume,
    unversioned,
)


def item(name, kind=None, enabled=True, group=False):
    return {
        "sourceName": name,
        "inputKind": kind,
        "sceneItemEnabled": enabled,
        "isGroup": group,
    }


class FakeClient:
    def __init__(self, scene="A", scenes=None, inputs=None, stuck_mute=False):
        self.scene = scene
        self.scenes = scenes or {}
        self.inputs = inputs or {}  # name -> [muted, volume_db]
        self.stuck_mute = stuck_mute
        self.calls = []

    def get_current_program_scene(self):
        return SimpleNamespace(current_program_scene_name=self.scene)

    def get_scene_item_list(self, name):
        return SimpleNamespace(scene_items=self.scenes[name])

    get_group_scene_item_list = get_scene_item_list

    def get_input_mute(self, name):
        return SimpleNamespace(input_muted=self.inputs[name][0])

    def get_input_volume(self, name):
        return SimpleNamespace(input_volume_db=self.inputs[name][1])

    def set_input_mute(self, name, muted):
        self.calls.append(("mute", name, muted))
        if not self.stuck_mute:
            self.inputs[name][0] = muted

    def set_input_volume(self, name, vol_mul=None, vol_db=None):
        self.calls.append(("volume", name, vol_db))
        self.inputs[name][1] = vol_db


def client(muted=False, db=-10.0, **kw):
    return FakeClient(
        scenes={"A": [item("Media", "ffmpeg_source_v2")]},
        inputs={"Media": [muted, db]},
        **kw,
    )


TARGET = InputTarget(scene_inputs={"A": ["Media"]}, input_kinds=["ffmpeg_source"])


def test_unversioned():
    assert unversioned("ffmpeg_source_v2") == "ffmpeg_source"
    assert unversioned("browser_source") == "browser_source"
    assert unversioned(None) == ""


def test_next_volume_bounds_and_monotonic():
    assert next_volume(-10, "up", 3, -40, 0) == -7
    assert next_volume(-2, "up", 3, -40, 0) == 0
    assert next_volume(0, "up", 3, -40, 0) == 0
    assert next_volume(5, "up", 3, -40, 0) == 5  # never lowered by an "up"
    assert next_volume(-38, "down", 3, -40, 0) == -40
    assert next_volume(-40, "down", 3, -40, 0) == -40
    assert next_volume(-60, "down", 3, -40, 0) == -60  # never raised by a "down"
    assert next_volume(-math.inf, "up", 3, -100, 0) == -97


def test_resolve_unmapped_scene_fails_closed():
    c = client(scene="B")
    with pytest.raises(OBSInputError):
        resolve_inputs(c, TARGET)
    assert c.calls == []


def test_resolve_input_not_visible_fails_closed():
    c = client()
    c.scenes["A"] = [item("Media", "ffmpeg_source_v2", enabled=False)]
    with pytest.raises(OBSInputError):
        resolve_inputs(c, TARGET)


def test_resolve_kind_filter():
    c = client()
    c.scenes["A"] = [item("Media", "image_source")]
    with pytest.raises(OBSInputError):
        resolve_inputs(c, TARGET)


def test_resolve_nested_scene_and_group():
    c = FakeClient(
        scenes={
            "A": [item("Nested"), item("Grp", "x", group=True)],
            "Nested": [item("Media", "ffmpeg_source")],
            "Grp": [item("Browser", "browser_source_v1")],
        },
        inputs={"Media": [False, -5.0], "Browser": [False, -5.0]},
    )
    target = InputTarget(
        scene_inputs={"A": ["Media", "Browser"]},
        input_kinds=["ffmpeg_source", "browser_source"],
    )
    assert resolve_inputs(c, target) == ("A", ["Media", "Browser"])


def test_resolve_scene_cycle_terminates():
    c = FakeClient(scenes={"A": [item("B")], "B": [item("A")]}, inputs={})
    with pytest.raises(OBSInputError):
        resolve_inputs(c, TARGET)


def test_resolve_named_input():
    c = client()
    assert resolve_inputs(c, InputTarget(input_name="Media")) == (None, ["Media"])
    with pytest.raises(KeyError):
        resolve_inputs(c, InputTarget(input_name="Nope"))


def test_set_mute_and_readback():
    c = client(muted=False)
    result = set_mute(c, TARGET, True)
    assert c.inputs["Media"][0] is True
    assert result.as_dict()["inputs"][0]["muted_before"] is False
    assert result.as_dict()["inputs"][0]["muted_after"] is True


def test_set_mute_readback_mismatch():
    c = client(stuck_mute=True)
    with pytest.raises(OBSInputError):
        set_mute(c, TARGET, True)


def test_step_down_preserves_mute():
    c = client(muted=True, db=-10)
    result = step_volume(c, TARGET, "down", 3, -40, 0, True)
    assert c.inputs["Media"] == [True, -13]
    assert ("mute", "Media", False) not in c.calls
    assert result.changes[0].muted_after is True


def test_step_up_unmutes():
    c = client(muted=True, db=-10)
    result = step_volume(c, TARGET, "up", 3, -40, 0, True)
    assert c.inputs["Media"] == [False, -7]
    assert result.changes[0].muted_after is False


def test_step_up_unmutes_at_ceiling_without_volume_write():
    c = client(muted=True, db=0)
    step_volume(c, TARGET, "up", 3, -40, 0, True)
    assert c.inputs["Media"] == [False, 0]
    assert not [call for call in c.calls if call[0] == "volume"]


def test_step_up_without_unmute_keeps_mute():
    c = client(muted=True, db=-10)
    step_volume(c, TARGET, "up", 3, -40, 0, False)
    assert c.inputs["Media"][0] is True


def test_step_clamps_at_floor():
    c = client(db=-39)
    step_volume(c, TARGET, "down", 3, -40, 0, False)
    assert c.inputs["Media"][1] == -40


def test_step_volume_minus_inf_is_floored():
    c = client(db=-math.inf)
    result = step_volume(c, TARGET, "up", 3, -100, 0, False)
    assert c.inputs["Media"][1] == -97
    assert result.changes[0].volume_db_before == -100.0


def test_nan_volume_rejected():
    c = client(db=math.nan)
    with pytest.raises(OBSInputError):
        step_volume(c, TARGET, "up", 3, -40, 0, True)


@pytest.mark.parametrize(
    ("step", "lo", "hi"),
    [
        (math.nan, -40, 0),
        (3, math.nan, 0),
        (3, -40, math.inf),
        (0, -40, 0),
        (-3, -40, 0),
        (3, 0, 0),
        (3, 0, -40),
        (3, -101, 0),
        (3, -40, 27),
    ],
)
def test_invalid_step_or_bounds(step, lo, hi):
    c = client()
    with pytest.raises(OBSInputError):
        step_volume(c, TARGET, "up", step, lo, hi, True)
    assert c.calls == []


def test_invalid_direction():
    with pytest.raises(OBSInputError):
        step_volume(client(), TARGET, "sideways", 3, -40, 0, True)


def test_off_scene_changes_nothing():
    c = client(scene="Other", muted=True, db=-10)
    with pytest.raises(OBSInputError):
        step_volume(c, TARGET, "up", 3, -40, 0, True)
    assert c.calls == []
