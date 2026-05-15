"""Tests for the strategy comparison harness (`compare.py`)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import compare


REPO_ROOT = Path(__file__).resolve().parents[1]
FIX_A = REPO_ROOT / "fixtures" / "strategies" / "a.yaml"
FIX_B = REPO_ROOT / "fixtures" / "strategies" / "b.yaml"


# --- Contract: output shape ----------------------------------------------

def test_compare_returns_a_b_delta_top_level_keys():
    result = compare.compare(FIX_A, FIX_B)
    assert set(result.keys()) == {"a", "b", "delta"}


def test_delta_contains_max_drawdown_pct():
    result = compare.compare(FIX_A, FIX_B)
    assert "max_drawdown_pct" in result["delta"]
    assert isinstance(result["delta"]["max_drawdown_pct"], float)


def test_each_side_carries_gauntlet_and_replay():
    result = compare.compare(FIX_A, FIX_B)
    for side in ("a", "b"):
        assert "gauntlet" in result[side]
        assert "replay" in result[side]
        assert "max_drawdown_pct" in result[side]
        assert {"passed", "vetoes", "checked"} <= set(result[side]["gauntlet"].keys())
        assert {"windows", "max_drawdown_pct", "worst_window"} <= set(result[side]["replay"].keys())


# --- Contract: delta semantics -------------------------------------------

def test_delta_max_drawdown_equals_b_minus_a():
    result = compare.compare(FIX_A, FIX_B)
    expected = round(result["b"]["max_drawdown_pct"] - result["a"]["max_drawdown_pct"], 2)
    assert result["delta"]["max_drawdown_pct"] == expected


def test_leveraged_candidate_has_worse_drawdown_than_baseline():
    """`b.yaml` is intentionally riskier, so delta must be positive."""
    result = compare.compare(FIX_A, FIX_B)
    assert result["delta"]["max_drawdown_pct"] > 0
    assert result["b"]["max_drawdown_pct"] > result["a"]["max_drawdown_pct"]


def test_per_window_delta_covers_all_three_canonical_windows():
    result = compare.compare(FIX_A, FIX_B)
    names = {w["window"] for w in result["delta"]["per_window_drawdown_delta"]}
    assert names == {"2008-gfc", "2020-covid", "2022-rates"}


# --- Determinism ---------------------------------------------------------

def test_compare_is_deterministic_same_inputs_same_output():
    one = compare.compare(FIX_A, FIX_B)
    two = compare.compare(FIX_A, FIX_B)
    assert json.dumps(one, sort_keys=True) == json.dumps(two, sort_keys=True)


def test_swapping_arguments_inverts_delta():
    forward = compare.compare(FIX_A, FIX_B)
    reverse = compare.compare(FIX_B, FIX_A)
    assert forward["delta"]["max_drawdown_pct"] == -reverse["delta"]["max_drawdown_pct"]


# --- Gauntlet integration -----------------------------------------------

def test_baseline_passes_gauntlet_and_candidate_fails_on_leverage():
    result = compare.compare(FIX_A, FIX_B)
    assert result["a"]["gauntlet"]["passed"] is True
    assert result["b"]["gauntlet"]["passed"] is False
    breached_caps = {v["cap"] for v in result["b"]["gauntlet"]["vetoes"]}
    assert "max_leverage" in breached_caps


# --- Error paths --------------------------------------------------------

def test_missing_file_raises_filenotfound(tmp_path):
    missing = tmp_path / "nope.yaml"
    with pytest.raises(FileNotFoundError):
        compare.compare(missing, FIX_B)


def test_non_mapping_yaml_rejected(tmp_path):
    bad = tmp_path / "list.yaml"
    bad.write_text("- 1\n- 2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        compare.compare(bad, FIX_B)


# --- CLI ----------------------------------------------------------------

def test_cli_stdout_matches_library(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "compare.py"), str(FIX_A), str(FIX_B)],
        capture_output=True,
        check=True,
        text=True,
    )
    cli_payload = json.loads(proc.stdout)
    lib_payload = compare.compare(FIX_A, FIX_B)
    assert cli_payload == lib_payload


def test_cli_writes_out_file_and_creates_parent_dirs(tmp_path):
    out = tmp_path / "deep" / "nested" / "result.json"
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "compare.py"),
            str(FIX_A),
            str(FIX_B),
            "--out",
            str(out),
        ],
        capture_output=True,
        check=True,
        text=True,
    )
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert set(payload.keys()) == {"a", "b", "delta"}


def test_cli_missing_file_exits_2(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(REPO_ROOT / "compare.py"), str(tmp_path / "nope.yaml"), str(FIX_B)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "not found" in proc.stderr
