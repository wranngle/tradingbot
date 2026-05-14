"""Tests for the black-swan replay harness."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "replay_blackswan.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("replay_blackswan", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["replay_blackswan"] = module
    spec.loader.exec_module(module)
    return module


replay_blackswan = _load_module()


@pytest.mark.parametrize("scenario", ["2008", "covid"])
def test_known_good_strategy_survives(scenario):
    """The cash-heavy known-good fixture survives both crash windows."""
    report = replay_blackswan.replay(scenario, strategy_key="cash_heavy")
    assert report["scenario"] == scenario
    assert report["survived"] is True
    assert 0.0 <= report["peak_drawdown_pct"] <= report["survival_max_drawdown_pct"]
    assert report["terminal_equity"] > 0
    assert report["bars"] > 0


@pytest.mark.parametrize(
    "scenario,min_dd",
    [("2008", 0.40), ("covid", 0.30)],
)
def test_buy_and_hold_takes_real_drawdown(scenario, min_dd):
    """Buy-and-hold through these windows must register a meaningful drawdown."""
    report = replay_blackswan.replay(scenario, strategy_key="buy_and_hold")
    assert report["peak_drawdown_pct"] >= min_dd, report


def test_cli_scenario_2008_exits_zero_and_prints_required_keys():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--scenario", "2008"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    for key in ("peak_drawdown_pct", "terminal_equity", "survived"):
        assert key in payload, f"missing {key} in {payload}"
    assert isinstance(payload["survived"], bool)


def test_cli_scenario_covid_exits_zero_and_prints_required_keys():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--scenario", "covid"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    for key in ("peak_drawdown_pct", "terminal_equity", "survived"):
        assert key in payload


def test_unknown_scenario_raises():
    with pytest.raises(ValueError, match="unknown scenario"):
        replay_blackswan.replay("dotcom")


def test_peak_drawdown_math():
    equity = [100.0, 120.0, 90.0, 110.0, 60.0, 80.0]
    # peak 120 → trough 60 → dd = 0.5
    assert replay_blackswan.peak_drawdown(equity) == pytest.approx(0.5)
