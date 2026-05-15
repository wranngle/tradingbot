"""Tests for `monte_carlo` — the position-size sanity tester.

Contract under test:
  - 100 seeded simulations produce a result with p50/p95/p99 drawdown_pct.
  - Drawdown percentiles are monotonically non-decreasing.
  - Same seed reproduces the same percentiles bit-for-bit.
  - Different seeds produce different distributions (sanity, not equality).
  - Riskier position sizes produce strictly worse p99 drawdown (rule-of-thumb
    validation that the simulation is responsive to the input it is sold on).
  - CLI invocation writes the same payload to stdout.
  - Input validation rejects nonsensical configs.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout

import pytest

from monte_carlo import SimConfig, main, run


DEFAULT_CFG = SimConfig(
    risk=0.02, win_rate=0.55, payoff=1.8, trades=250, sims=100, seed=42
)


# central-promise e2e: 100 sims, monotonic drawdown percentiles in output
def test_e2e_100_sims_emits_monotonic_drawdown_percentiles():
    result = run(DEFAULT_CFG)
    assert result.p50_drawdown_pct <= result.p95_drawdown_pct <= result.p99_drawdown_pct
    assert result.p99_drawdown_pct <= result.worst_drawdown_pct
    assert 0 <= result.p50_drawdown_pct <= 100
    assert 0 <= result.p99_drawdown_pct <= 100


def test_seeded_runs_are_deterministic():
    a = run(DEFAULT_CFG)
    b = run(DEFAULT_CFG)
    assert a == b


def test_different_seeds_produce_different_distributions():
    a = run(DEFAULT_CFG)
    b = run(SimConfig(**{**DEFAULT_CFG.__dict__, "seed": 999}))
    # not asserting full inequality of every field — just that the seed
    # actually fans out the RNG (p50 OR p95 should differ)
    assert (a.p50_drawdown_pct, a.p95_drawdown_pct) != (b.p50_drawdown_pct, b.p95_drawdown_pct)


def test_higher_risk_yields_worse_p99_drawdown():
    safe = run(SimConfig(**{**DEFAULT_CFG.__dict__, "risk": 0.01}))
    aggressive = run(SimConfig(**{**DEFAULT_CFG.__dict__, "risk": 0.10}))
    assert aggressive.p99_drawdown_pct > safe.p99_drawdown_pct


def test_cli_emits_json_with_required_keys():
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main([
            "--risk", "0.02", "--win-rate", "0.55", "--payoff", "1.8",
            "--trades", "250", "--sims", "100", "--seed", "42",
        ])
    assert rc == 0
    payload = json.loads(buf.getvalue())
    for key in ("p50_drawdown_pct", "p95_drawdown_pct", "p99_drawdown_pct"):
        assert key in payload
    assert payload["p50_drawdown_pct"] <= payload["p95_drawdown_pct"] <= payload["p99_drawdown_pct"]
    assert payload["config"]["seed"] == 42
    assert payload["config"]["sims"] == 100


@pytest.mark.parametrize("field,value", [
    ("risk", 0.0), ("risk", 1.5),
    ("win_rate", 0.0), ("win_rate", 1.0),
    ("payoff", 0.0), ("payoff", -1.0),
    ("trades", 0),
    ("sims", 0),
])
def test_invalid_configs_raise(field, value):
    cfg = SimConfig(**{**DEFAULT_CFG.__dict__, field: value})
    with pytest.raises(ValueError):
        run(cfg)


def test_ruin_path_records_ruined_count():
    # Tilt the simulation hard against survival: high risk, low win rate.
    # Some paths should hit equity <= starting capital.
    cfg = SimConfig(risk=0.40, win_rate=0.30, payoff=1.0, trades=50, sims=100, seed=7)
    result = run(cfg)
    assert result.ruined_sim_count > 0
    assert result.p99_drawdown_pct > result.p50_drawdown_pct
