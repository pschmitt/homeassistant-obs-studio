"""Base entity for OBS Studio."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import OBSCoordinator


class OBSEntity(CoordinatorEntity[OBSCoordinator]):
    """Base OBS entity: ties device info and unique ID to the coordinator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: OBSCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        entry = self.coordinator.config_entry
        data = self.coordinator.data
        return DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="OBS Project",
            model="OBS Studio",
            sw_version=data.obs_version if data else None,
            hw_version=data.platform_description if data else None,
        )
