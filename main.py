#!/usr/bin/env python3
"""Polymarket NVIDIA CEO forecaster.

Strategy (validated on the 6 practice cases, loss ~0.31 vs house baseline 0.36):
- Median: persistence. Prediction-market prices are a martingale, so the
  current price is the best median forecast. Momentum drift was tested and
  HURTS (it adds loss), so drift is exactly zero.
- Spread: per-market robust volatility. Each market gets its own sigma,
  estimated from the standard deviation of its 1-minute returns over the
  last 12 hours (720 minutes), with the top/bottom 2% trimmed so rare huge
  jumps don't inflate it. Floored at 0.0002, capped at 0.005.
- Quantiles: q_tau = x + z_tau * sigma * sqrt(h), clamped to [0, 1],
  rounded to 6 decimals. z_tau are the standard normal quantiles.

Every market always gets a forecast (sigma floor guarantees output even
for flat/empty histories), every minute gets all five quantiles, and the
program is deterministic (no randomness, no clock, no network).
"""
import json
import math
import os
import statistics
import sys

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

QUANTILES = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.644854, -0.67449, 0.0, 0.67449, 1.644854]

WINDOW = 720          # minutes of history for the volatility estimate
TRIM = 0.02           # trim 2% of returns from each tail (jump-robust)
SIGMA_FLOOR = 0.0002  # never narrower than this (keeps output valid)
SIGMA_CAP = 0.005     # never wider than this (avoids paying on quiet minutes)


def price6(x):
    """Clamp to [0, 1] and round to 6 decimals (0, never -0)."""
    v = round(min(1.0, max(0.0, x)) * 1e6) / 1e6
    return v + 0.0


def sigma_of(prices):
    """Robust per-market sigma: trimmed std of 1-min returns, last 12h."""
    seg = prices[-WINDOW:] if len(prices) > WINDOW else prices
    if len(seg) < 2:
        return SIGMA_FLOOR
    rets = [seg[i + 1] - seg[i] for i in range(len(seg) - 1)]
    if not rets:
        return SIGMA_FLOOR
    ordered = sorted(rets)
    n = len(ordered)
    k = max(1, int(n * TRIM))
    trimmed = ordered[k:-k] if n > 2 * k else ordered
    if len(trimmed) < 2:
        return SIGMA_FLOOR
    sd = statistics.pstdev(trimmed)
    return min(SIGMA_CAP, max(SIGMA_FLOOR, sd))


def forecast_market(market, horizon):
    """240 rows x 5 quantiles for one market. Never raises, never skips."""
    prices = market.get("prices") or []
    x = prices[-1] if prices else 0.5
    sigma = sigma_of(prices)
    rows = []
    for h in range(1, horizon + 1):
        spread = sigma * math.sqrt(h)
        rows.append([price6(x + z * spread) for z in Z])
    return rows


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    names = sorted(f for f in os.listdir(INPUT_DIR) if f.endswith(".in"))
    for name in names:
        case_id = name[: -len(".in")]
        with open(os.path.join(INPUT_DIR, name), "r", encoding="utf-8") as fh:
            case = json.load(fh)
        horizon = int(case.get("horizon_minutes", 240))
        forecasts = []
        for market in case.get("markets", []):
            forecasts.append({
                "id": market["id"],
                "q": forecast_market(market, horizon),
            })
        out_path = os.path.join(OUTPUT_DIR, case_id + ".out")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"forecasts": forecasts}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
