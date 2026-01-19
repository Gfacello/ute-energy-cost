"""Config flow for UTE Tariff."""
from __future__ import annotations

import json
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_APPLY_VAT_TO_FIXED,
    CONF_CONTRACTED_POWER_KW,
    CONF_ENERGY_ENTITY_ID,
    CONF_HOLIDAYS_LIST,
    CONF_INCLUDE_FIXED,
    CONF_INCLUDE_POWER,
    CONF_INCLUDE_VAT,
    CONF_MODE,
    CONF_PRICE_TABLE_OVERRIDE,
    CONF_PUNTA_WINDOW,
    CONF_TARIFF,
    CONF_TIMEZONE,
    CONF_USE_HOLIDAYS,
    CONF_VAT_RATE,
    DEFAULT_HOLIDAYS_2026,
    DEFAULT_TIMEZONE,
    DOMAIN,
    MODE_AVERAGE,
    MODE_BILL_LIKE,
    MODE_MARGINAL,
    PUNTA_WINDOWS,
    TARIFF_TRD,
    TARIFF_TRT,
    TARIFF_TRS,
)

_LOGGER = logging.getLogger(__name__)


class UteTariffConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UTE Tariff."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            await self._warn_if_energy_entity_invalid(user_input[CONF_ENERGY_ENTITY_ID])
            return self.async_create_entry(title="UTE Tariff", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ENERGY_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig()
                ),
                vol.Required(CONF_TARIFF, default=TARIFF_TRS): vol.In(
                    [TARIFF_TRS, TARIFF_TRD, TARIFF_TRT]
                ),
                vol.Required(CONF_MODE, default=MODE_MARGINAL): vol.In(
                    [MODE_MARGINAL, MODE_AVERAGE, MODE_BILL_LIKE]
                ),
                vol.Optional(CONF_TIMEZONE, default=DEFAULT_TIMEZONE): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema)

    async def _warn_if_energy_entity_invalid(self, entity_id: str) -> None:
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            _LOGGER.warning("Energy entity %s is unavailable during setup", entity_id)
            return

        device_class = state.attributes.get("device_class")
        state_class = state.attributes.get("state_class")
        if device_class != "energy" or state_class != "total_increasing":
            _LOGGER.warning(
                "Energy entity %s should have device_class=energy and state_class=total_increasing",
                entity_id,
            )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return UteTariffOptionsFlowHandler(config_entry.hass, config_entry)


class UteTariffOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for UTE Tariff."""

    def __init__(self, hass, entry: config_entries.ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            options = self._normalize_options(user_input, errors)
            if not errors:
                return self.async_create_entry(title="", data=options)

        options = self.entry.options
        schema = vol.Schema(
            {
                vol.Optional(CONF_TARIFF, default=options.get(CONF_TARIFF, TARIFF_TRS)): vol.In(
                    [TARIFF_TRS, TARIFF_TRD, TARIFF_TRT]
                ),
                vol.Optional(CONF_MODE, default=options.get(CONF_MODE, MODE_MARGINAL)): vol.In(
                    [MODE_MARGINAL, MODE_AVERAGE, MODE_BILL_LIKE]
                ),
                vol.Optional(CONF_PUNTA_WINDOW, default=options.get(CONF_PUNTA_WINDOW, "18-22")): vol.In(
                    PUNTA_WINDOWS
                ),
                vol.Optional(CONF_USE_HOLIDAYS, default=options.get(CONF_USE_HOLIDAYS, False)): bool,
                vol.Optional(
                    CONF_HOLIDAYS_LIST,
                    default=",".join(options.get(CONF_HOLIDAYS_LIST, DEFAULT_HOLIDAYS_2026)),
                ): str,
                vol.Optional(
                    CONF_INCLUDE_FIXED,
                    default=options.get(CONF_INCLUDE_FIXED, False),
                ): bool,
                vol.Optional(
                    CONF_INCLUDE_POWER,
                    default=options.get(CONF_INCLUDE_POWER, False),
                ): bool,
                vol.Optional(
                    CONF_CONTRACTED_POWER_KW,
                    default=options.get(CONF_CONTRACTED_POWER_KW, 0.0),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_INCLUDE_VAT,
                    default=options.get(CONF_INCLUDE_VAT, False),
                ): bool,
                vol.Optional(
                    CONF_VAT_RATE,
                    default=options.get(CONF_VAT_RATE, 0.22),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_APPLY_VAT_TO_FIXED,
                    default=options.get(CONF_APPLY_VAT_TO_FIXED, False),
                ): bool,
                vol.Optional(
                    CONF_PRICE_TABLE_OVERRIDE,
                    default=options.get(CONF_PRICE_TABLE_OVERRIDE, ""),
                ): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)

    def _normalize_options(self, user_input: dict[str, Any], errors: dict[str, str]) -> dict[str, Any]:
        options = dict(user_input)

        holidays_raw = options.get(CONF_HOLIDAYS_LIST, "")
        if isinstance(holidays_raw, str):
            holidays_list = [
                item.strip() for item in holidays_raw.split(",") if item.strip()
            ]
        else:
            holidays_list = list(holidays_raw)
        options[CONF_HOLIDAYS_LIST] = holidays_list

        include_power = options.get(CONF_INCLUDE_POWER, False)
        if include_power and options.get(CONF_CONTRACTED_POWER_KW, 0.0) <= 0:
            errors[CONF_CONTRACTED_POWER_KW] = "contracted_power_required"

        override = options.get(CONF_PRICE_TABLE_OVERRIDE)
        if override:
            try:
                json.loads(override)
            except ValueError:
                errors[CONF_PRICE_TABLE_OVERRIDE] = "invalid_json"

        return options
