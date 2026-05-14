"""Market regime detection.

Emits one of `bull | bear | choppy | crisis` from a rolling price series,
using two signals:

* annualised realised volatility over `window` daily returns
* peak-to-trough drawdown of the series over the same window

Thresholds are conservative and tuned against the canned fixtures under
``tests/`` (steady uptrend = bull, sustained decline = bear, oscillating =
choppy, March-2020-style collapse = crisis). They are intentionally simple
so the classifier is auditable, not hyper-fit.

Usage::

    from regime import classify_regime
    label = classify_regime(prices)   # "bull" | "bear" | "choppy" | "crisis"

Designed to be import-safe outside the QuantConnect runtime; no
``AlgorithmImports`` dependency.
"""

from __future__ import annotations

import math
from typing import Iterable, Literal, Sequence

RegimeLabel = Literal["bull", "bear", "choppy", "crisis"]

# Thresholds, expressed in annualised / fractional terms.
CRISIS_DRAWDOWN = 0.20      # >=20% peak-to-trough -> crisis
CRISIS_VOL = 0.60           # OR annualised vol >= 60%
BEAR_RETURN = -0.05         # total return over window <= -5% AND not crisis
BULL_RETURN = 0.05          # total return over window >= +5% AND vol moderate
CHOPPY_VOL = 0.35           # vol above this with neither trend => choppy
TRADING_DAYS = 252


def _daily_returns(prices: Sequence[float]) -> list[float]:
    return [prices[i] / prices[i - 1] - 1.0 for i in range(1, len(prices))]


def _annualised_vol(returns: Sequence[float]) -> float:
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(var) * math.sqrt(TRADING_DAYS)


def _max_drawdown(prices: Sequence[float]) -> float:
    peak = prices[0]
    worst = 0.0
    for p in prices:
        if p > peak:
            peak = p
        dd = (peak - p) / peak if peak > 0 else 0.0
        if dd > worst:
            worst = dd
    return worst


def classify_regime(prices: Iterable[float], window: int | None = None) -> RegimeLabel:
    """Return the regime label for the trailing ``window`` of ``prices``.

    ``prices`` must contain at least 2 points. ``window`` defaults to the
    full series; if larger than the series it is clamped.
    """
    series = [float(p) for p in prices]
    if len(series) < 2:
        raise ValueError("classify_regime requires at least 2 price points")
    if window is not None and window > 1:
        series = series[-window:]

    returns = _daily_returns(series)
    vol = _annualised_vol(returns)
    drawdown = _max_drawdown(series)
    total_return = series[-1] / series[0] - 1.0

    if drawdown >= CRISIS_DRAWDOWN or vol >= CRISIS_VOL:
        return "crisis"
    if total_return <= BEAR_RETURN:
        return "bear"
    if total_return >= BULL_RETURN and vol < CHOPPY_VOL:
        return "bull"
    return "choppy"


def classify_regime_verbose(prices: Iterable[float], window: int | None = None) -> dict:
    """Same as ``classify_regime`` but returns the supporting signals.

    Useful for logging from inside the algorithm so an operator can audit
    why a particular label fired.
    """
    series = [float(p) for p in prices]
    if window is not None and window > 1:
        series = series[-window:]
    returns = _daily_returns(series)
    return {
        "label": classify_regime(series),
        "annualised_vol": _annualised_vol(returns),
        "max_drawdown": _max_drawdown(series),
        "total_return": series[-1] / series[0] - 1.0,
        "window_size": len(series),
    }
