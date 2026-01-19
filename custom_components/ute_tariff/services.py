"""Services for UTE Tariff."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    DOMAIN,
    SERVICE_FIELD_ROUND_DIGITS,
    SERVICE_FIELD_TARGET_ENTITY_ID,
    SERVICE_FIELD_VALUE_SOURCE,
    SERVICE_SET_VALUE,
    VALUE_SOURCE_AVG_MONTH,
    VALUE_SOURCE_COST_MONTH,
    VALUE_SOURCE_COST_TODAY,
    VALUE_SOURCE_EFF_MONTH,
    VALUE_SOURCE_PRICE_NOW,
)
from .coordinator import UteTariffCoordinator

_LOGGER = logging.getLogger(__name__)


def async_register_services(hass: HomeAssistant) -> None:
    if hass.data.get(DOMAIN, {}).get("services_registered"):
        return

    async def handle_set_value(call: ServiceCall) -> None:
        target_entity_id = call.data[SERVICE_FIELD_TARGET_ENTITY_ID]
        value_source = call.data[SERVICE_FIELD_VALUE_SOURCE]
        round_digits = call.data.get(SERVICE_FIELD_ROUND_DIGITS, 3)

        if not target_entity_id.startswith("input_number."):
            _LOGGER.error("Target entity must be input_number, got %s", target_entity_id)
            return

        coordinator = _pick_coordinator(hass)
        if coordinator is None:
            _LOGGER.error("No UTE Tariff coordinator available")
            return

        value = _resolve_value(coordinator, value_source)
        if value is None:
            _LOGGER.error("Value source %s is unavailable", value_source)
            return

        await hass.services.async_call(
            "input_number",
            "set_value",
            {"entity_id": target_entity_id, "value": round(value, round_digits)},
            blocking=True,
        )

    hass.services.async_register(DOMAIN, SERVICE_SET_VALUE, handle_set_value)
    hass.data[DOMAIN]["services_registered"] = True


def _pick_coordinator(hass: HomeAssistant) -> UteTariffCoordinator | None:
    entries = hass.data.get(DOMAIN, {})
    for value in entries.values():
        if isinstance(value, UteTariffCoordinator):
            return value
    return None


def _resolve_value(coordinator: UteTariffCoordinator, value_source: str) -> float | None:
    data = coordinator.data

    if value_source == VALUE_SOURCE_PRICE_NOW:
        return coordinator.compute_price_now()
    if value_source == VALUE_SOURCE_AVG_MONTH:
        return coordinator.compute_average_price()
    if value_source == VALUE_SOURCE_EFF_MONTH:
        return coordinator.compute_effective_price()
    if value_source == VALUE_SOURCE_COST_TODAY:
        return data.get("cost_today")
    if value_source == VALUE_SOURCE_COST_MONTH:
        return data.get("cost_month")

    return None

