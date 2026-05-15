"""Behaviour tests for the daily risk-state digest.

What this asserts (and why each test would actually fail on a real regression):

* happy-path: the four contract headings plus at least one data row appear.
  Drift here means the digest no longer covers a section the operator relies
  on, which is a real downstream break.
* determinism: same input bytes -> byte-identical output bytes. Drift here
  means git diffs become noisy and CI cannot gate on a clean digest.
* empty-state: a brand-new deployment with no history still renders all four
  headings with ``no data`` placeholders, instead of crashing.
* CLI: ``--input`` -> stdout writes the same bytes ``build_digest`` produced
  on the same fixture (locks the end-to-end contract, not just the library).
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

import risk_digest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "fixtures" / "digest_input.json"

REQUIRED_HEADINGS = (
    "## Drawdown",
    "## Regime",
    "## Gauntlet history (last 7d)",
    "## Exposure by asset",
)


@pytest.fixture
def state() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_all_required_headings_and_one_data_row(state):
    digest = risk_digest.build_digest(state)
    for heading in REQUIRED_HEADINGS:
        assert heading in digest, f"missing section: {heading}"
    # At least one data row from the bundled fixture must be present.
    assert "core" in digest
    assert "SPY" in digest


def test_deterministic_same_input_same_bytes(state):
    a = risk_digest.build_digest(state)
    b = risk_digest.build_digest(state)
    assert a == b


def test_determinism_independent_of_key_order(state):
    shuffled_exposure = dict(reversed(list(state["exposure_by_asset"].items())))
    shuffled_history = list(reversed(state["gauntlet_history"]))
    shuffled = {**state, "exposure_by_asset": shuffled_exposure, "gauntlet_history": shuffled_history}
    assert risk_digest.build_digest(state) == risk_digest.build_digest(shuffled)


def test_empty_state_renders_no_data_placeholders():
    digest = risk_digest.build_digest({})
    for heading in REQUIRED_HEADINGS:
        assert heading in digest
    assert digest.count("_no data_") == 4


def test_partial_state_only_marks_missing_sections():
    partial = {"regime": "bull", "current_drawdown_pct": 0.1, "max_drawdown_cap": 0.3}
    digest = risk_digest.build_digest(partial)
    # Drawdown + regime present, gauntlet + exposure marked as no data.
    assert "bull" in digest
    assert "10.00%" in digest
    assert digest.count("_no data_") == 2


def test_cli_stdout_matches_library(monkeypatch, capsys):
    rc = risk_digest.main(["--input", str(FIXTURE)])
    captured = capsys.readouterr()
    expected = risk_digest.build_digest(json.loads(FIXTURE.read_text(encoding="utf-8")))
    assert rc == 0
    assert captured.out == expected


def test_cli_out_file_writes_and_creates_parents(tmp_path):
    target = tmp_path / "nested" / "digest.md"
    rc = risk_digest.main(["--input", str(FIXTURE), "--out", str(target)])
    assert rc == 0
    assert target.exists()
    assert target.read_text(encoding="utf-8") == risk_digest.build_digest(
        json.loads(FIXTURE.read_text(encoding="utf-8"))
    )
