"""Regime-detection tests.

Four fixture price series, each with a known label. Series are
deterministic so the classifier's behavior is auditable; no random
inputs and no external data files.
"""

from __future__ import annotations

import math

import pytest

from regime import classify_regime, classify_regime_verbose


def _compound(start: float, daily_returns):
    out = [start]
    for r in daily_returns:
        out.append(out[-1] * (1.0 + r))
    return out


# Fixture 1: steady uptrend, low vol -> bull.
BULL_PRICES = _compound(100.0, [0.002] * 60)

# Fixture 2: steady downtrend, low-ish vol but >5% total decline -> bear.
BEAR_PRICES = _compound(100.0, [-0.002] * 60)

# Fixture 3: oscillating sideways, no clear trend -> choppy.
CHOPPY_PRICES = _compound(
    100.0,
    [0.015, -0.014, 0.013, -0.012, 0.011, -0.010] * 10,
)

# Fixture 4: March-2020-style collapse -> crisis.
# Linear 35% drawdown over ~20 sessions.
def _crisis_series():
    prices = [100.0]
    daily_drop = (1.0 - 0.65) ** (1.0 / 20.0)
    for _ in range(20):
        prices.append(prices[-1] * daily_drop)
    # tack on a noisy recovery to mimic real March/April 2020
    for r in [0.05, -0.03, 0.04, -0.02, 0.03, -0.04, 0.02, -0.01]:
        prices.append(prices[-1] * (1.0 + r))
    return prices


CRISIS_PRICES = _crisis_series()


@pytest.mark.parametrize(
    "label,series",
    [
        ("bull", BULL_PRICES),
        ("bear", BEAR_PRICES),
        ("choppy", CHOPPY_PRICES),
        ("crisis", CRISIS_PRICES),
    ],
)
def test_classify_regime_label_matches_fixture(label, series):
    assert classify_regime(series) == label


def test_verbose_payload_shape():
    out = classify_regime_verbose(CRISIS_PRICES)
    assert out["label"] == "crisis"
    assert set(out) == {"label", "annualised_vol", "max_drawdown", "total_return", "window_size"}
    assert out["max_drawdown"] >= 0.20
    assert math.isfinite(out["annualised_vol"])


def test_window_truncation_isolates_trailing_leg():
    # Long bull leg, then a flat sideways tail. Full series = bull,
    # trailing 30-bar window with no drift => choppy/bear depending on noise.
    flat_tail = _compound(BULL_PRICES[-1], [0.0, -0.001, 0.001, -0.002, 0.002] * 6)
    combined = BULL_PRICES + flat_tail[1:]
    assert classify_regime(combined) == "bull"
    # Trailing window only sees the flat tail (no >5% gain, no >5% loss).
    assert classify_regime(combined, window=len(flat_tail)) == "choppy"


def test_requires_two_points():
    with pytest.raises(ValueError):
        classify_regime([100.0])
