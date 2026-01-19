# UTE Tariff (Uruguay)

Home Assistant custom integration to calculate UTE residential electricity costs and kWh prices based on the TRS, TRD, or TRT tariffs.

## Installation (HACS)
1. In HACS, add this repository as a custom repository (type: Integration).
2. Install **UTE Tariff (Uruguay)**.
3. Restart Home Assistant.

## Setup
1. Go to **Settings > Devices & Services > Add Integration**.
2. Search for **UTE Tariff**.
3. Pick your energy sensor (device_class: energy, state_class: total_increasing).
4. Choose your tariff, mode, and timezone.

## Options
- Tariff: TRS, TRD, TRT
- Mode: marginal, average, bill_like
- Punta window: 17-21, 18-22, 19-23 (weekdays only)
- Holidays list: comma-separated list of `YYYY-MM-DD`
- Bill-like options: include fixed and power charges, contracted power kW
- VAT: apply VAT to energy only by default; optional apply to fixed/power
- Price table override: JSON string that replaces the default price table

### Punta window
The punta window is the 4-hour peak block for weekdays only. Example: `18-22` means peak from 18:00 to 21:59 local time.

### Holidays list
The options default to a built-in 2026 list (fixed-date holidays only). You can edit it to match your calendar. Use `use_holidays` and populate `holidays_list` with dates, for example:

```
2026-01-01, 2026-05-01, 2026-12-25
```

## Service: `ute_tariff.set_value`
Write a computed value into an `input_number`:

```yaml
service: ute_tariff.set_value
data:
  target_entity_id: input_number.ute_price_kwh
  value_source: price_kwh_now
  round_digits: 3
```

### Value sources
- `price_kwh_now`
- `avg_kwh_month`
- `effective_kwh_month`
- `cost_today`
- `cost_month`

## Notes
- Costs and breakdowns depend on sensor update frequency. Sparse updates can shift which time-of-use bucket receives energy.
- Monthly TRS tiers are calculated across the entire month. Daily cost is accumulated from each delta using the current tier.

## License
MIT
