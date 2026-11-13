# Polymarket NVIDIA CEO forecaster

Forecasts Polymarket's "Next CEO of NVIDIA?" Yes prices, 240 minutes ahead,
5 quantiles per minute. Entry for make.fun polymarket-nvidia-ceo-forecast-01.

Strategy: persistence median (prediction-market prices are a martingale;
momentum drift was tested and hurts) + per-market robust volatility
(trimmed std of 1-min returns over the last 12h, floored/capped).
Practice loss ~0.31 vs house baseline 0.36.
