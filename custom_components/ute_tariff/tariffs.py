"""Tariff calculation helpers for UTE Tariff."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

from zoneinfo import ZoneInfo

from .const import PUNTA_WINDOWS, TARIFF_TRD, TARIFF_TRT, TARIFF_TRS


DEFAULT_PRICE_TABLE: dict[str, Any] = {
    "TRS": {
        "tiers": [
            {"limit": 100.0, "price": 6.744},
            {"limit": 600.0, "price": 8.452},
            {"limit": None, "price": 10.539},
        ],
        "fixed_charge_month": 324.9,
        "power_charge_per_kw": 83.2,
    },
    "TRD": {
        "offpeak_kwh": 4.771,
        "peak_kwh": 12.034,
        "fixed_charge_month": 488.0,
        "power_charge_per_kw": 83.2,
    },
    "TRT": {
        "valley_kwh": 2.443,
        "flat_kwh": 5.172,
        "peak_kwh": 12.034,
        "fixed_charge_month": 488.0,
        "power_charge_per_kw": 83.2,
    },
}


@dataclass
class PeriodInfo:
    period: str
    is_peak: bool
    is_holiday: bool


def parse_punta_window(window: str) -> tuple[int, int]:
    if window not in PUNTA_WINDOWS:
        window = "18-22"
    start, end = window.split("-")
    return int(start), int(end)


def is_business_day(local_date: date, use_holidays: bool, holidays_list: list[str]) -> bool:
    if local_date.weekday() >= 5:
        return False
    if use_holidays and local_date.isoformat() in holidays_list:
        return False
    return True


def classify_period(
    tariff: str,
    now: datetime,
    punta_window: str,
    use_holidays: bool,
    holidays_list: list[str],
    timezone: str,
) -> PeriodInfo:
    tz = ZoneInfo(timezone)
    local_dt = now.astimezone(tz)
    local_date = local_dt.date()
    business_day = is_business_day(local_date, use_holidays, holidays_list)
    start_hour, end_hour = parse_punta_window(punta_window)
    is_peak = business_day and start_hour <= local_dt.hour < end_hour

    if tariff == TARIFF_TRD:
        period = "peak" if is_peak else "offpeak"
    elif tariff == TARIFF_TRT:
        if local_dt.time() < time(7, 0):
            period = "valley"
            is_peak = False
        else:
            if business_day and is_peak:
                period = "peak"
            else:
                period = "flat"
                is_peak = False
    else:
        period = "tiers"
        is_peak = False

    return PeriodInfo(period=period, is_peak=is_peak, is_holiday=not business_day)


def trs_cost_for_delta(prev_total_kwh: float, delta_kwh: float, prices: dict[str, Any]) -> float:
    tiers = prices["tiers"]
    remaining = delta_kwh
    cost = 0.0
    current_total = prev_total_kwh

    for tier in tiers:
        price = tier["price"]
        limit = tier["limit"]
        if remaining <= 0:
            break

        if limit is None:
            cost += remaining * price
            remaining = 0
            break

        tier_span = max(0.0, limit - current_total)
        if tier_span <= 0:
            current_total = limit
            continue

        take = min(remaining, tier_span)
        cost += take * price
        remaining -= take
        current_total += take

    if remaining > 0:
        cost += remaining * tiers[-1]["price"]

    return cost


def trs_tier_breakdown(total_kwh: float, prices: dict[str, Any]) -> dict[str, float]:
    tier1 = min(total_kwh, 100.0)
    tier2 = min(max(total_kwh - 100.0, 0.0), 500.0)
    tier3 = max(total_kwh - 600.0, 0.0)
    price1 = prices["tiers"][0]["price"]
    price2 = prices["tiers"][1]["price"]
    price3 = prices["tiers"][2]["price"]

    return {
        "kwh_tier1": tier1,
        "kwh_tier2": tier2,
        "kwh_tier3": tier3,
        "cost_tier1": tier1 * price1,
        "cost_tier2": tier2 * price2,
        "cost_tier3": tier3 * price3,
    }


def trs_marginal_price(total_kwh: float, prices: dict[str, Any]) -> float:
    if total_kwh <= 100.0:
        return prices["tiers"][0]["price"]
    if total_kwh <= 600.0:
        return prices["tiers"][1]["price"]
    return prices["tiers"][2]["price"]

