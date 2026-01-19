"""Sensors for UTE Tariff."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_BREAKDOWN,
    ATTR_IS_HOLIDAY_TODAY,
    ATTR_IS_PEAK_NOW,
    ATTR_LAST_UPDATE_TS,
    ATTR_MODE,
    ATTR_PUNTA_WINDOW,
    ATTR_TARIFF,
    ATTR_TIMEZONE,
    CONF_MODE,
    CONF_PUNTA_WINDOW,
    CONF_TARIFF,
    CONF_TIMEZONE,
    DOMAIN,
    MODE_AVERAGE,
    MODE_BILL_LIKE,
    MODE_MARGINAL,
)
from .coordinator import UteTariffCoordinator


@dataclass
class UteSensorDescription:
    key: str
    name: str
    unit: str | None
    device_class: SensorDeviceClass | None
    state_class: SensorStateClass | None
    suggested_unit_of_measurement: str | None = None
    has_entity_name: bool = True


SENSORS: list[UteSensorDescription] = [
    UteSensorDescription(
        key="price_kwh_now",
        name="UTE Tariff Price kWh Now",
        unit="UYU/kWh",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    UteSensorDescription(
        key="cost_today",
        name="UTE Tariff Cost Today",
        unit="UYU",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    UteSensorDescription(
        key="cost_month",
        name="UTE Tariff Cost Month",
        unit="UYU",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    UteSensorDescription(
        key="kwh_today",
        name="UTE Tariff kWh Today",
        unit="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    UteSensorDescription(
        key="kwh_month",
        name="UTE Tariff kWh Month",
        unit="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    coordinator: UteTariffCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        UteTariffSensor(coordinator, entry, description) for description in SENSORS
    ]
    async_add_entities(entities)


class UteTariffSensor(CoordinatorEntity[UteTariffCoordinator], SensorEntity):
    """UTE Tariff sensor."""

    def __init__(
        self,
        coordinator: UteTariffCoordinator,
        entry: ConfigEntry,
        description: UteSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_class = description.device_class
        self._attr_state_class = description.state_class
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="UTE Tariff",
            manufacturer="UTE",
            model=self._entry.options.get(CONF_TARIFF, self._entry.data.get(CONF_TARIFF)),
        )

    @property
    def native_value(self) -> float | None:
        key = self.entity_description.key
        data = self.coordinator.data

        if key == "price_kwh_now":
            mode = self._current_mode
            if mode == MODE_MARGINAL:
                return self.coordinator.compute_price_now()
            if mode == MODE_AVERAGE:
                return self.coordinator.compute_average_price()
            if mode == MODE_BILL_LIKE:
                return self.coordinator.compute_effective_price()
            return None

        return data.get(key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        options = self._entry.options

        attrs = {
            ATTR_TARIFF: options.get(CONF_TARIFF, self._entry.data.get(CONF_TARIFF)),
            ATTR_MODE: options.get(CONF_MODE, self._entry.data.get(CONF_MODE)),
            ATTR_PUNTA_WINDOW: options.get(CONF_PUNTA_WINDOW, "18-22"),
            ATTR_TIMEZONE: options.get(CONF_TIMEZONE, self._entry.data.get(CONF_TIMEZONE)),
            ATTR_BREAKDOWN: data.get("breakdown", {}),
            ATTR_LAST_UPDATE_TS: data.get("last_update_ts"),
        }

        period_info = self.coordinator.current_period_info()
        attrs[ATTR_IS_HOLIDAY_TODAY] = period_info["is_holiday_today"]
        attrs[ATTR_IS_PEAK_NOW] = period_info["is_peak_now"]

        return attrs

    @property
    def _current_mode(self) -> str:
        return self._entry.options.get(CONF_MODE, self._entry.data.get(CONF_MODE))
