"""Config flow for CasaTunes."""
from __future__ import annotations

import logging
from urllib.parse import urlparse

from pycasatunes import CasaTunes
from pycasatunes.exceptions import CasaException
import async_timeout
import voluptuous as vol

from homeassistant.components.ssdp import (
    ATTR_SSDP_LOCATION,
    ATTR_UPNP_FRIENDLY_NAME,
    ATTR_UPNP_SERIAL,
)

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.device_registry import format_mac

from .const import DOMAIN

DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})

ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_UNKNOWN = "unknown"

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    """Validate the user input allows us to connect.
    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    session = async_get_clientsession(hass)
    casa = CasaTunes(session, data[CONF_HOST])
    system = await casa.get_system()

    return {
        "title": system.AppName,
        "mac_address": format_mac(system.MACAddress),
    }


class CasaTunesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a CasaTunes config flow."""

    def __init__(self):
        """Set up the instance."""
        self.discovery_info = {}
        self.data_schema = {
            vol.Required("host"): str,
        }

    @callback
    def _show_form(self, errors: dict | None = None) -> FlowResult:
        """Show the form to the user."""
        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors or {},
        )

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle a flow initialized by the user."""
        if not user_input:
            return self._show_form()

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CasaException:
            _LOGGER.debug("CasaTunes Error", exc_info=True)
            errors["base"] = ERROR_CANNOT_CONNECT
            return self._show_form(errors)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unknown error trying to connect")
            return self.async_abort(reason=ERROR_UNKNOWN)

        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=vol.Schema(self.data_schema)
            )

        await self.async_set_unique_id(format_mac(info["mac_address"]))
        self._abort_if_unique_id_configured(updates={CONF_HOST: user_input[CONF_HOST]})

        return self.async_create_entry(
            title=info["title"],
            data=user_input,
        )

    async def async_step_ssdp(self, discovery_info: DiscoveryInfoType) -> FlowResult:
        """Handle a flow initialized by discovery."""
        host = urlparse(discovery_info[ATTR_SSDP_LOCATION]).hostname
        name = discovery_info[ATTR_UPNP_FRIENDLY_NAME]

        try:
            mac = await self._async_get_mac(host)
        except CasaException:
            return self.async_abort(reason="cannot_connect")
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unknown error trying to connect")
            return self.async_abort(reason=ERROR_UNKNOWN)

        await self.async_set_unique_id(format_mac(mac))
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        self.context.update({"title_placeholders": {"name": name}})

        self.discovery_info.update({CONF_HOST: host, CONF_NAME: name})

        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle user-confirmation of discovered system."""
        if user_input is None:
            return self.async_show_form(
                step_id="discovery_confirm",
                description_placeholders={"name": self.discovery_info[CONF_NAME]},
                errors={},
            )

        return self.async_create_entry(
            title=self.discovery_info[CONF_NAME],
            data=self.discovery_info,
        )

    async def _async_get_mac(self, host: str) -> str:
        """Get system MAC address."""
        session = async_get_clientsession(self.hass)
        casa = CasaTunes(session, host)

        with async_timeout.timeout(30):
            system = await casa.get_system()

        if system.MACAddress is not None:
            return system.MACAddress
