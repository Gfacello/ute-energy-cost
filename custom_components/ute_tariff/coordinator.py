"""Coordinator for UTE Tariff."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

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
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEZONE,
    DOMAIN,
    MAX_DELTA_KWH,
    MODE_AVERAGE,
    MODE_BILL_LIKE,
    MODE_MARGINAL,
    TARIFF_TRD,
    TARIFF_TRT,
    TARIFF_TRS,
)
from .tariffs import (
    DEFAULT_PRICE_TABLE,
    classify_period,
    trs_cost_for_delta,
    trs_marginal_price,
    trs_tier_breakdown,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class TariffOptions:
    tariff: str
    mode: str
    timezone: str
    punta_window: str
    use_holidays: bool
    holidays_list: list[str]
    include_fixed: bool
    include_power: bool
    contracted_power_kw: float
    include_vat: bool
    vat_rate: float
    apply_vat_to_fixed: bool
    price_table: dict[str, Any]


class UteTariffCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Update coordinator for UTE Tariff."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.entry = entry
        self._store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        self._unsub_state_change = None

    async def async_initialize(self) -> None:
        stored = await self._store.async_load()
        if stored is None:
            stored = {}
        self.data = self._default_state(stored)

        energy_entity_id = self.entry.data.get(CONF_ENERGY_ENTITY_ID)
        if energy_entity_id:
            self._unsub_state_change = async_track_state_change_event(
                self.hass, [energy_entity_id], self._handle_state_change
            )

        await self.async_config_entry_first_refresh()

    async def async_reload_options(self) -> None:
        await self.async_request_refresh()

    @callback
    def _handle_state_change(self, event) -> None:
        self.async_request_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        energy_entity_id = self.entry.data.get(CONF_ENERGY_ENTITY_ID)
        if not energy_entity_id:
            return self.data

        options = self._get_options()

        now_utc = dt_util.utcnow()
        local_now = now_utc.astimezone(dt_util.get_time_zone(options.timezone))
        self._reset_if_needed(local_now)

        state = self.hass.states.get(energy_entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            _LOGGER.debug("Energy entity unavailable: %s", energy_entity_id)
            self.data["last_update_ts"] = local_now.isoformat()
            await self._store.async_save(self.data)
            return self.data

        try:
            current_energy = float(state.state)
        except ValueError:
            _LOGGER.warning("Invalid energy state for %s: %s", energy_entity_id, state.state)
            self.data["last_update_ts"] = local_now.isoformat()
            await self._store.async_save(self.data)
            return self.data

        last_energy = self.data.get("last_energy_value")
        delta = 0.0
        if last_energy is not None:
            delta = current_energy - last_energy
        if delta < 0 or delta > MAX_DELTA_KWH:
            _LOGGER.warning(
                "Energy delta reset detected for %s (last=%s current=%s)",
                energy_entity_id,
                last_energy,
                current_energy,
            )
            delta = 0.0

        if delta > 0:
            self._apply_delta(delta, options, local_now)

        self.data["last_energy_value"] = current_energy
        self.data["last_update_ts"] = local_now.isoformat()

        await self._store.async_save(self.data)

        return self.data

    def _default_state(self, stored: dict[str, Any]) -> dict[str, Any]:
        return {
            "last_energy_value": stored.get("last_energy_value"),
            "last_update_ts": stored.get("last_update_ts"),
            "kwh_today": stored.get("kwh_today", 0.0),
            "kwh_month": stored.get("kwh_month", 0.0),
            "cost_today": stored.get("cost_today", 0.0),
            "cost_month": stored.get("cost_month", 0.0),
            "breakdown": stored.get("breakdown", {}),
            "last_reset_day": stored.get("last_reset_day"),
            "last_reset_month": stored.get("last_reset_month"),
        }

    def _get_options(self) -> TariffOptions:
        data = self.entry.data
        opts = self.entry.options

        tariff = opts.get(CONF_TARIFF, data.get(CONF_TARIFF, TARIFF_TRS))
        mode = opts.get(CONF_MODE, data.get(CONF_MODE, MODE_MARGINAL))
        timezone = opts.get(CONF_TIMEZONE, data.get(CONF_TIMEZONE, DEFAULT_TIMEZONE))
        punta_window = opts.get(CONF_PUNTA_WINDOW, "18-22")
        use_holidays = opts.get(CONF_USE_HOLIDAYS, False)
        holidays_list = opts.get(CONF_HOLIDAYS_LIST, DEFAULT_HOLIDAYS_2026)
        include_fixed = opts.get(CONF_INCLUDE_FIXED, False)
        include_power = opts.get(CONF_INCLUDE_POWER, False)
        contracted_power_kw = opts.get(CONF_CONTRACTED_POWER_KW, 0.0)
        include_vat = opts.get(CONF_INCLUDE_VAT, False)
        vat_rate = opts.get(CONF_VAT_RATE, 0.22)
        apply_vat_to_fixed = opts.get(CONF_APPLY_VAT_TO_FIXED, False)

        price_table = DEFAULT_PRICE_TABLE
        override = opts.get(CONF_PRICE_TABLE_OVERRIDE)
        if override:
            try:
                price_table = json.loads(override)
            except (ValueError, TypeError):
                _LOGGER.warning("Invalid price_table_override JSON; using defaults")

        return TariffOptions(
            tariff=tariff,
            mode=mode,
            timezone=timezone,
            punta_window=punta_window,
            use_holidays=use_holidays,
            holidays_list=holidays_list,
            include_fixed=include_fixed,
            include_power=include_power,
            contracted_power_kw=contracted_power_kw,
            include_vat=include_vat,
            vat_rate=vat_rate,
            apply_vat_to_fixed=apply_vat_to_fixed,
            price_table=price_table,
        )

    def _reset_if_needed(self, local_now: datetime) -> None:
        day_key = local_now.date().isoformat()
        month_key = local_now.replace(day=1).date().isoformat()

        if self.data.get("last_reset_day") != day_key:
            self.data["kwh_today"] = 0.0
            self.data["cost_today"] = 0.0
            self.data["last_reset_day"] = day_key

        if self.data.get("last_reset_month") != month_key:
            self.data["kwh_month"] = 0.0
            self.data["cost_month"] = 0.0
            self.data["breakdown"] = {}
            self.data["last_reset_month"] = month_key

    def _apply_delta(self, delta: float, options: TariffOptions, local_now: datetime) -> None:
        self.data["kwh_today"] += delta
        prev_kwh_month = self.data["kwh_month"]
        self.data["kwh_month"] += delta

        breakdown = self.data.get("breakdown", {})

        if options.tariff == TARIFF_TRS:
            cost_delta = trs_cost_for_delta(prev_kwh_month, delta, options.price_table["TRS"])
            self.data["cost_today"] += cost_delta
            self.data["cost_month"] += cost_delta
            breakdown = trs_tier_breakdown(self.data["kwh_month"], options.price_table["TRS"])
        else:
            period_info = classify_period(
                options.tariff,
                local_now,
                options.punta_window,
                options.use_holidays,
                options.holidays_list,
                options.timezone,
            )
            if options.tariff == TARIFF_TRD:
                rate = options.price_table["TRD"][f"{period_info.period}_kwh"]
                key_kwh = f"kwh_{period_info.period}"
                key_cost = f"cost_{period_info.period}"
            else:
                rate = options.price_table["TRT"][f"{period_info.period}_kwh"]
                key_kwh = f"kwh_{period_info.period}"
                key_cost = f"cost_{period_info.period}"

            breakdown[key_kwh] = breakdown.get(key_kwh, 0.0) + delta
            breakdown[key_cost] = breakdown.get(key_cost, 0.0) + (delta * rate)

            self.data["cost_today"] += delta * rate
            self.data["cost_month"] += delta * rate

        self.data["breakdown"] = breakdown

    def compute_price_now(self) -> float | None:
        options = self._get_options()
        if options.tariff == TARIFF_TRS:
            return trs_marginal_price(self.data.get("kwh_month", 0.0), options.price_table["TRS"])

        now = dt_util.utcnow()
        period_info = classify_period(
            options.tariff,
            now,
            options.punta_window,
            options.use_holidays,
            options.holidays_list,
            options.timezone,
        )
        key = f"{period_info.period}_kwh"
        return options.price_table[options.tariff][key]

    def compute_average_price(self) -> float | None:
        kwh_month = self.data.get("kwh_month", 0.0)
        if kwh_month <= 0:
            return None
        return self.data.get("cost_month", 0.0) / kwh_month

    def compute_effective_price(self) -> float | None:
        options = self._get_options()
        kwh_month = self.data.get("kwh_month", 0.0)
        if kwh_month <= 0:
            return None

        energy_cost = self.data.get("cost_month", 0.0)

        fixed = 0.0
        if options.include_fixed:
            fixed = options.price_table[options.tariff]["fixed_charge_month"]

        power = 0.0
        if options.include_power:
            power = options.price_table[options.tariff]["power_charge_per_kw"] * options.contracted_power_kw

        if options.include_vat:
            energy_cost *= 1 + options.vat_rate
            if options.apply_vat_to_fixed:
                fixed *= 1 + options.vat_rate
                power *= 1 + options.vat_rate

        total = energy_cost + fixed + power
        return total / kwh_month

    def current_period_info(self) -> dict[str, Any]:
        options = self._get_options()
        now = dt_util.utcnow()
        period_info = classify_period(
            options.tariff,
            now,
            options.punta_window,
            options.use_holidays,
            options.holidays_list,
            options.timezone,
        )
        return {
            "is_holiday_today": period_info.is_holiday,
            "is_peak_now": period_info.is_peak,
        }

    async def async_shutdown(self) -> None:
        if self._unsub_state_change:
            self._unsub_state_change()
