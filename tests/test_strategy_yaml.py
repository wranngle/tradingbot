"""Strategy lifecycle YAML schema tests.

Behaviors under test:
- Repo-checked-in `strategy.yaml` parses cleanly into the pydantic schema.
- Malformed YAML (wrong stage, missing field, out-of-range cap) raises with a
  message that names the offending field — caller can surface it usefully.
- CLI returns exit 0 / non-zero matching parse success.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from validate_strategy import Strategy, load_strategy, main  # noqa: E402


REPO_STRATEGY = PROJECT_ROOT / "strategy.yaml"


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "strategy.yaml"
    p.write_text(body, encoding="utf-8")
    return p


def test_repo_strategy_yaml_loads():
    strategy = load_strategy(REPO_STRATEGY)
    assert strategy.stage in {"local", "paper", "live"}
    assert strategy.notional_cap > 0
    assert strategy.promotion_criteria.min_paper_trades >= 1


def test_invalid_stage_rejected_with_field_name(tmp_path):
    body = (
        "stage: prod\n"
        "notional_cap: 1000\n"
        "version: \"0.1.0\"\n"
        "promotion_criteria:\n"
        "  min_paper_trades: 50\n"
        "  min_sharpe: 1.2\n"
        "  max_drawdown_pct: 0.15\n"
        "  min_paper_days: 30\n"
    )
    target = _write(tmp_path, body)
    with pytest.raises(ValidationError) as exc:
        load_strategy(target)
    assert "stage" in str(exc.value)


def test_missing_promotion_criteria_field_rejected(tmp_path):
    body = (
        "stage: paper\n"
        "notional_cap: 1000\n"
        "version: \"0.1.0\"\n"
        "promotion_criteria:\n"
        "  min_paper_trades: 50\n"
        "  min_sharpe: 1.2\n"
        "  max_drawdown_pct: 0.15\n"
    )
    target = _write(tmp_path, body)
    with pytest.raises(ValidationError) as exc:
        load_strategy(target)
    assert "min_paper_days" in str(exc.value)


def test_negative_notional_cap_rejected(tmp_path):
    body = (
        "stage: local\n"
        "notional_cap: -10\n"
        "version: \"0.1.0\"\n"
        "promotion_criteria:\n"
        "  min_paper_trades: 50\n"
        "  min_sharpe: 1.2\n"
        "  max_drawdown_pct: 0.15\n"
        "  min_paper_days: 30\n"
    )
    target = _write(tmp_path, body)
    with pytest.raises(ValidationError) as exc:
        load_strategy(target)
    assert "notional_cap" in str(exc.value)


def test_malformed_version_rejected(tmp_path):
    body = (
        "stage: local\n"
        "notional_cap: 1000\n"
        "version: \"v1\"\n"
        "promotion_criteria:\n"
        "  min_paper_trades: 50\n"
        "  min_sharpe: 1.2\n"
        "  max_drawdown_pct: 0.15\n"
        "  min_paper_days: 30\n"
    )
    target = _write(tmp_path, body)
    with pytest.raises(ValidationError) as exc:
        load_strategy(target)
    assert "version" in str(exc.value)


def test_cli_exit_zero_on_repo_strategy():
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "validate_strategy.py")],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_cli_exit_nonzero_on_bad_file(tmp_path):
    bad = _write(tmp_path, "stage: bogus\nnotional_cap: 100\n")
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "validate_strategy.py"), str(bad)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "validation failed" in result.stderr


def test_main_returns_one_on_missing_file(tmp_path):
    missing = tmp_path / "nope.yaml"
    rc = main(["validate_strategy.py", str(missing)])
    assert rc == 1


def test_strategy_model_round_trip():
    data = {
        "stage": "live",
        "notional_cap": 5000,
        "version": "1.2.3",
        "promotion_criteria": {
            "min_paper_trades": 100,
            "min_sharpe": 1.5,
            "max_drawdown_pct": 0.10,
            "min_paper_days": 60,
        },
    }
    s = Strategy(**data)
    assert s.stage == "live"
    assert s.promotion_criteria.min_sharpe == 1.5
