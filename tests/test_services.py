"""Schema and handler tests that need Home Assistant installed.

Skipped when ``homeassistant`` is not importable (it is not a test dependency of
the repository). The OBS client is replaced by a fake.
"""

from __future__ import annotations

import asyncio
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("homeassistant")
pytest.importorskip("obsws_python")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import voluptuous as vol  # noqa: E402
from homeassistant.core import HomeAssistant  # noqa: E402
from homeassistant.exceptions import ServiceValidationError  # noqa: E402
from test_inputs import FakeClient, item  # noqa: E402

from custom_components.obs_studio import services  # noqa: E402
from custom_components.obs_studio.const import DOMAIN  # noqa: E402
from custom_components.obs_studio.inputs import (  # noqa: E402
    set_mute,
    step_volume,
)

SCENES = {"scene_inputs": {"A": ["Media"]}, "input_kinds": ["ffmpeg_source"]}


def test_mute_schema():
    schema = services._SET_INPUT_MUTE_SCHEMA
    assert schema({"muted": True, **SCENES})["muted"] is True
    with pytest.raises(vol.Invalid):
        schema({"muted": True})  # no target
    with pytest.raises(vol.Invalid):
        schema({"muted": True, "input_name": "x", **SCENES})  # both targets
    with pytest.raises(vol.Invalid):
        schema(SCENES)  # muted missing
    with pytest.raises(vol.Invalid):
        schema({"muted": True, "scene_inputs": {"A": []}})
    with pytest.raises(vol.Invalid):
        schema({"muted": True, "input_name": ""})


def test_unknown_keys_rejected_but_ha_targets_allowed():
    mute = services._SET_INPUT_MUTE_SCHEMA
    with pytest.raises(vol.Invalid):
        mute({"muted": True, "typo": 1, **SCENES})
    assert mute({"muted": True, "entity_id": ["select.x"], **SCENES})
    step = services._STEP_INPUT_VOLUME_SCHEMA
    with pytest.raises(vol.Invalid):
        step({"direction": "up", "step_db": 3, "unmute_up": True, **SCENES})
    assert step({"direction": "up", "step_db": 3, "device_id": "d", **SCENES})


def test_step_schema_defaults_and_rejections():
    schema = services._STEP_INPUT_VOLUME_SCHEMA
    out = schema({"direction": "up", "step_db": 3, **SCENES})
    assert (out["min_db"], out["max_db"], out["unmute_on_up"]) == (-100.0, 0.0, False)
    for bad in (
        {"direction": "left", "step_db": 3},
        {"direction": "up", "step_db": math.nan},
        {"direction": "up", "step_db": math.inf},
        {"direction": "up", "step_db": 0},
        {"direction": "up", "step_db": 3, "min_db": math.nan},
        {"direction": "up", "step_db": 3, "max_db": 27},
        {"direction": "up", "step_db": 3, "min_db": -101},
        {"direction": "up", "step_db": 3, "min_db": 0, "max_db": 0},
        {"direction": "up", "step_db": 3, "min_db": -10, "max_db": -20},
        {"direction": "up", "step_db": True},
    ):
        with pytest.raises(vol.Invalid):
            schema({**bad, **SCENES})


class FakeOBSClient:
    """Stands in for OBSClient: same method names, backed by a fake websocket."""

    def __init__(self, ws):
        self.ws = ws
        self.active = 0
        self.max_active = 0

    def _track(self):
        self.active += 1
        self.max_active = max(self.max_active, self.active)

    def set_input_mute(self, target, muted):
        self._track()
        try:
            return set_mute(self.ws, target, muted)
        finally:
            self.active -= 1

    def step_input_volume(self, target, *args):
        self._track()
        try:
            return step_volume(self.ws, target, *args)
        finally:
            self.active -= 1


@pytest.fixture
def ws():
    return FakeClient(
        scene="A",
        scenes={"A": [item("Media", "ffmpeg_source_v2")]},
        inputs={"Media": [True, -10.0]},
    )


async def _hass(tmp_path, ws, monkeypatch):
    hass = HomeAssistant(str(tmp_path))
    client = FakeOBSClient(ws)
    entry = SimpleNamespace(runtime_data=SimpleNamespace(audio_lock=asyncio.Lock(), client=client))
    monkeypatch.setattr(services, "_get_entry", lambda _hass, _call: entry)
    services.async_setup_services(hass)
    return hass, client


def test_service_round_trip(tmp_path, ws, monkeypatch):
    async def run():
        hass, _ = await _hass(tmp_path, ws, monkeypatch)
        result = await hass.services.async_call(
            DOMAIN,
            "step_input_volume",
            {
                "direction": "up",
                "step_db": 3,
                "min_db": -40,
                "max_db": 0,
                "unmute_on_up": True,
                **SCENES,
            },
            blocking=True,
            return_response=True,
        )
        assert result["scene"] == "A"
        assert result["inputs"][0]["volume_db_after"] == -7.0
        assert result["inputs"][0]["muted_after"] is False
        assert ws.inputs["Media"] == [False, -7.0]

        result = await hass.services.async_call(
            DOMAIN,
            "set_input_mute",
            {"muted": True, **SCENES},
            blocking=True,
            return_response=True,
        )
        assert result["inputs"][0]["muted_after"] is True

        ws.scene = "Other"
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                DOMAIN, "set_input_mute", {"muted": False, **SCENES}, blocking=True
            )
        assert ws.inputs["Media"][0] is True

    asyncio.run(run())


def test_concurrent_calls_are_serialised(tmp_path, ws, monkeypatch):
    async def run():
        hass, client = await _hass(tmp_path, ws, monkeypatch)
        ws.inputs["Media"] = [False, -40.0]
        data = {"direction": "up", "step_db": 3, "min_db": -40, "max_db": 0, **SCENES}
        await asyncio.gather(
            *(
                hass.services.async_call(DOMAIN, "step_input_volume", data, blocking=True)
                for _ in range(4)
            )
        )
        assert client.max_active == 1
        assert ws.inputs["Media"][1] == -28.0  # no lost updates

    asyncio.run(run())
