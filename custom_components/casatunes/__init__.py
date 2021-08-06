"""The CasaTunes integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from aiohttp.client_exceptions import ClientResponseError
from pycasatunes import CasaTunes
from pycasatunes.exceptions import CasaException
from pycasatunes.objects.system import CasaTunesSystem
from pycasatunes.objects.zone import CasaTunesZone
import async_timeout
import voluptuous as vol

from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from .const import DOMAIN

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = [MEDIA_PLAYER_DOMAIN]
_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(seconds=15)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CasaTunes from a config entry."""

    client = CasaTunes(async_get_clientsession(hass), entry.data[CONF_HOST])
    coordinator = CasaTunesDataUpdateCoordinator(hass, client=client)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class CasaTunesDataUpdateCoordinator(DataUpdateCoordinator[CasaTunes]):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, client: CasaTunes) -> None:
        """Initialize."""
        self.casatunes = client

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.entities: list[CasaTunesDeviceEntity] = []

    async def _async_update_data(self) -> CasaTunes:
        """Update data via library."""
        try:
            await self.casatunes.fetch()
        except CasaException as exception:
            raise UpdateFailed() from exception

        return self.casatunes


class CasaTunesEntity(CoordinatorEntity):
    """Defines a base CasaTunes entity."""

    def __init__(
        self,
        coordinator: CasaTunesDataUpdateCoordinator,
        zone: CasaTunesZone,
        device_id: str,
        zone_id: str,
    ) -> None:
        """Initialize the AL-KO entity."""
        super().__init__(coordinator)
        self._zone_id = zone_id
        self._zone = zone
        self._device_id = device_id
        self._name = zone.Name

    @property
    def zone_id(self) -> str:
        """Return the zone_id of the entity."""
        return self._zone_id

    @property
    def name(self) -> str:
        """Return the zone_id of the entity."""
        return self._name

    @property
    def system(self) -> CasaTunesSystem:
        """Get the CasaTunes System."""
        return self.coordinator.data.system

    @property
    def zone(self) -> CasaTunesZone:
        """Get the CasaTunes Zones."""
        return self.coordinator.data.zones_dict[self._zone_id]


class CasaTunesDeviceEntity(CasaTunesEntity):
    """Defines a CasaTunes device entity."""

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this CasaTunes instance."""
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "manufacturer": "CasaTunes",
            "name": self._name,
            "sw_version": self.system.CasaTunesVersion,
        }
