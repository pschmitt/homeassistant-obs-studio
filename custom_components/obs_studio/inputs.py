"""Audio input helpers: resolve the active input(s) and change mute or volume.

These functions operate on an ``obsws_python.ReqClient``-like object and are kept
free of Home Assistant imports so they can be tested in isolation. The caller
must serialise access to the client (see ``OBSClient``).
"""

from __future__ import annotations

import math
import re
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field

from .exceptions import OBSInputError

# OBS input volume is reported as -inf (muted fader) up to +26 dB; the websocket
# protocol clamps -100 dB as the floor.
OBS_MIN_DB = -100.0
OBS_MAX_DB = 26.0
MAX_SCENE_DEPTH = 8


@dataclass(frozen=True)
class InputTarget:
    """Which inputs a request applies to.

    Either ``input_name`` names one input directly, or ``scene_inputs`` maps a
    program-scene name to the input names allowed to be acted on while that scene
    is on air. ``input_kinds`` optionally restricts the OBS input kinds (version
    suffixes such as ``_v2`` are ignored).
    """

    input_name: str | None = None
    scene_inputs: Mapping[str, Sequence[str]] | None = None
    input_kinds: Collection[str] | None = None


@dataclass
class InputChange:
    """Before/after state of one input."""

    name: str
    muted_before: bool
    muted_after: bool
    volume_db_before: float
    volume_db_after: float

    def as_dict(self) -> dict[str, object]:
        return {
            "input": self.name,
            "muted_before": self.muted_before,
            "muted_after": self.muted_after,
            "volume_db_before": self.volume_db_before,
            "volume_db_after": self.volume_db_after,
        }


@dataclass
class InputResult:
    """Outcome of a request: the program scene and the inputs that were acted on."""

    scene: str | None
    changes: list[InputChange] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {"scene": self.scene, "inputs": [change.as_dict() for change in self.changes]}


def unversioned(kind: str | None) -> str:
    """Strip an OBS input-kind version suffix (``ffmpeg_source_v2`` -> ``ffmpeg_source``)."""
    return re.sub(r"_v\d+$", "", kind or "")


def _collect(
    client,
    scene: str,
    allowed: Collection[str],
    kinds: Collection[str] | None,
    found: list[str],
    visited: set[str],
    depth: int = 0,
    group: bool = False,
) -> None:
    """Walk the enabled items of a scene or group, gathering allowed inputs."""
    if scene in visited or depth > MAX_SCENE_DEPTH:
        return
    visited.add(scene)
    lister = client.get_group_scene_item_list if group else client.get_scene_item_list
    for item in lister(scene).scene_items:
        if not item.get("sceneItemEnabled"):
            continue
        name = item.get("sourceName")
        kind = item.get("inputKind")
        if item.get("isGroup"):
            _collect(client, name, allowed, kinds, found, visited, depth + 1, group=True)
        elif kind is None:
            # A nested scene: its items are on air too.
            _collect(client, name, allowed, kinds, found, visited, depth + 1)
        elif (
            name in allowed and (kinds is None or unversioned(kind) in kinds) and name not in found
        ):
            found.append(name)


def resolve_inputs(client, target: InputTarget) -> tuple[str | None, list[str]]:
    """Return ``(program scene, input names to act on)``.

    Fails closed: raises :class:`OBSInputError` when the program scene has no
    entry in ``scene_inputs`` or none of its allowed inputs is visible.
    """
    if target.input_name is not None:
        client.get_input_mute(target.input_name)  # raises if the input does not exist
        return None, [target.input_name]

    scene = client.get_current_program_scene().current_program_scene_name
    allowed = (target.scene_inputs or {}).get(scene)
    if not allowed:
        raise OBSInputError(f"no inputs are configured for the program scene {scene!r}")
    kinds = None if target.input_kinds is None else {unversioned(k) for k in target.input_kinds}
    found: list[str] = []
    _collect(client, scene, set(allowed), kinds, found, set())
    if not found:
        raise OBSInputError(f"no allowed input is visible on the program scene {scene!r}")
    return scene, found


def _read(client, name: str) -> tuple[bool, float]:
    muted = bool(client.get_input_mute(name).input_muted)
    volume = float(client.get_input_volume(name).input_volume_db)
    if math.isnan(volume):
        raise OBSInputError(f"OBS reported an invalid volume for {name!r}")
    return muted, max(volume, OBS_MIN_DB)


def _verify_mute(client, names: Sequence[str], muted: bool) -> None:
    for name in names:
        if bool(client.get_input_mute(name).input_muted) != muted:
            state = "muted" if muted else "unmuted"
            raise OBSInputError(f"{name!r} did not report {state}")


def set_mute(client, target: InputTarget, muted: bool) -> InputResult:
    """Mute or unmute the resolved inputs and verify OBS reports the new state."""
    scene, names = resolve_inputs(client, target)
    before = {name: _read(client, name) for name in names}
    for name in names:
        client.set_input_mute(name, muted)
    _verify_mute(client, names, muted)
    result = InputResult(scene)
    for name in names:
        result.changes.append(
            InputChange(name, before[name][0], muted, before[name][1], before[name][1])
        )
    return result


def next_volume(
    current_db: float, direction: str, step_db: float, min_db: float, max_db: float
) -> float:
    """Next dB value: bounded and monotonic in the requested direction."""
    current_db = max(current_db, OBS_MIN_DB)
    if direction == "up":
        if current_db >= max_db:
            return current_db
        return min(current_db + step_db, max_db)
    if current_db <= min_db:
        return current_db
    return max(current_db - step_db, min_db)


def step_volume(
    client,
    target: InputTarget,
    direction: str,
    step_db: float,
    min_db: float,
    max_db: float,
    unmute_on_up: bool,
) -> InputResult:
    """Step the resolved inputs' volume within ``[min_db, max_db]``.

    ``direction="up"`` with ``unmute_on_up`` also unmutes, even when the volume is
    already at the ceiling. Stepping down never changes the mute state.
    """
    if direction not in ("up", "down"):
        raise OBSInputError(f"invalid direction {direction!r}")
    for value in (step_db, min_db, max_db):
        if not math.isfinite(value):
            raise OBSInputError("step and bounds must be finite numbers")
    if step_db <= 0 or not OBS_MIN_DB <= min_db < max_db <= OBS_MAX_DB:
        raise OBSInputError("invalid step or volume bounds")

    scene, names = resolve_inputs(client, target)
    before = {name: _read(client, name) for name in names}
    after_db: dict[str, float] = {}
    for name in names:
        current = before[name][1]
        new = next_volume(current, direction, step_db, min_db, max_db)
        if new != current:
            client.set_input_volume(name, vol_db=new)
        after_db[name] = new
    unmute = direction == "up" and unmute_on_up
    if unmute:
        for name in names:
            client.set_input_mute(name, False)
        _verify_mute(client, names, False)
    result = InputResult(scene)
    for name in names:
        muted_after = False if unmute else before[name][0]
        result.changes.append(
            InputChange(name, before[name][0], muted_after, before[name][1], after_db[name])
        )
    return result
