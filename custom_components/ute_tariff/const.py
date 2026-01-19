"""Constants for UTE Tariff."""
from __future__ import annotations

DOMAIN = "ute_tariff"
NAME = "UTE Tariff (Uruguay)"

DEFAULT_TIMEZONE = "America/Montevideo"
DEFAULT_SCAN_INTERVAL = 30

CONF_ENERGY_ENTITY_ID = "energy_entity_id"
CONF_TARIFF = "tariff"
CONF_MODE = "mode"
CONF_TIMEZONE = "timezone"

CONF_PUNTA_WINDOW = "punta_window"
CONF_USE_HOLIDAYS = "use_holidays"
CONF_HOLIDAYS_LIST = "holidays_list"
CONF_INCLUDE_FIXED = "include_fixed_charge"
CONF_INCLUDE_POWER = "include_power_charge"
CONF_CONTRACTED_POWER_KW = "contracted_power_kw"
CONF_INCLUDE_VAT = "include_vat"
CONF_VAT_RATE = "vat_rate"
CONF_APPLY_VAT_TO_FIXED = "apply_vat_to_fixed_charge"
CONF_PRICE_TABLE_OVERRIDE = "price_table_override"

TARIFF_TRS = "TRS"
TARIFF_TRD = "TRD"
TARIFF_TRT = "TRT"

MODE_MARGINAL = "marginal"
MODE_AVERAGE = "average"
MODE_BILL_LIKE = "bill_like"

PUNTA_WINDOWS = ["17-21", "18-22", "19-23"]

DEFAULT_HOLIDAYS_2026 = [
    "2026-01-01",
    "2026-05-01",
    "2026-07-18",
    "2026-08-25",
    "2026-12-25",
]

SERVICE_SET_VALUE = "set_value"
SERVICE_FIELD_TARGET_ENTITY_ID = "target_entity_id"
SERVICE_FIELD_VALUE_SOURCE = "value_source"
SERVICE_FIELD_ROUND_DIGITS = "round_digits"

VALUE_SOURCE_PRICE_NOW = "price_kwh_now"
VALUE_SOURCE_AVG_MONTH = "avg_kwh_month"
VALUE_SOURCE_EFF_MONTH = "effective_kwh_month"
VALUE_SOURCE_COST_TODAY = "cost_today"
VALUE_SOURCE_COST_MONTH = "cost_month"

ATTR_TARIFF = "tariff"
ATTR_MODE = "mode"
ATTR_PUNTA_WINDOW = "punta_window"
ATTR_TIMEZONE = "timezone"
ATTR_IS_HOLIDAY_TODAY = "is_holiday_today"
ATTR_IS_PEAK_NOW = "is_peak_now"
ATTR_BREAKDOWN = "breakdown"
ATTR_LAST_UPDATE_TS = "last_update_ts"

STORAGE_KEY = "ute_tariff_state"
STORAGE_VERSION = 1

MAX_DELTA_KWH = 100000.0
