"""Tests for `veto_ledger` — record/tail/hook + CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import veto_ledger


@pytest.fixture
def ledger_path(tmp_path: Path) -> Path:
    return tmp_path / "vetoes.jsonl"


def test_record_veto_appends_row_with_all_fields(ledger_path: Path) -> None:
    row = veto_ledger.record_veto(
        "T-1", "momentum", "exceeds max_position_pct", ledger_path=ledger_path
    )
    assert row["trade_id"] == "T-1"
    assert row["strategy"] == "momentum"
    assert row["reason"] == "exceeds max_position_pct"
    assert row["timestamp"]
    stored = json.loads(ledger_path.read_text().strip())
    assert stored == row


def test_record_veto_creates_parent_dir(tmp_path: Path) -> None:
    nested = tmp_path / "deep" / "logs" / "vetoes.jsonl"
    veto_ledger.record_veto("T-2", "meanrev", "gauntlet drawdown", ledger_path=nested)
    assert nested.exists()


def test_record_veto_is_append_only(ledger_path: Path) -> None:
    veto_ledger.record_veto("T-1", "s", "r1", ledger_path=ledger_path)
    veto_ledger.record_veto("T-2", "s", "r2", ledger_path=ledger_path)
    veto_ledger.record_veto("T-3", "s", "r3", ledger_path=ledger_path)
    lines = ledger_path.read_text().splitlines()
    assert [json.loads(line)["trade_id"] for line in lines] == ["T-1", "T-2", "T-3"]


def test_tail_returns_last_n_oldest_first(ledger_path: Path) -> None:
    for i in range(1, 8):
        veto_ledger.record_veto(f"T-{i}", "s", f"r{i}", ledger_path=ledger_path)
    last = veto_ledger.tail(3, ledger_path=ledger_path)
    assert [r["trade_id"] for r in last] == ["T-5", "T-6", "T-7"]


def test_tail_missing_ledger_returns_empty(tmp_path: Path) -> None:
    assert veto_ledger.tail(5, ledger_path=tmp_path / "absent.jsonl") == []


def test_tail_zero_returns_empty(ledger_path: Path) -> None:
    veto_ledger.record_veto("T-1", "s", "r", ledger_path=ledger_path)
    assert veto_ledger.tail(0, ledger_path=ledger_path) == []


def test_tail_skips_malformed_lines(ledger_path: Path) -> None:
    veto_ledger.record_veto("T-1", "s", "r1", ledger_path=ledger_path)
    with ledger_path.open("a") as fh:
        fh.write("not-json\n")
    veto_ledger.record_veto("T-2", "s", "r2", ledger_path=ledger_path)
    last = veto_ledger.tail(5, ledger_path=ledger_path)
    assert [r["trade_id"] for r in last] == ["T-1", "T-2"]


def test_veto_if_records_when_predicate_failed(ledger_path: Path) -> None:
    vetoed = veto_ledger.veto_if(
        True, trade_id="T-9", strategy="momentum", reason="leverage cap", ledger_path=ledger_path
    )
    assert vetoed is True
    rows = veto_ledger.tail(5, ledger_path=ledger_path)
    assert len(rows) == 1
    assert rows[0]["reason"] == "leverage cap"


def test_veto_if_skips_when_predicate_passed(ledger_path: Path) -> None:
    vetoed = veto_ledger.veto_if(
        False, trade_id="T-9", strategy="momentum", reason="n/a", ledger_path=ledger_path
    )
    assert vetoed is False
    assert veto_ledger.tail(5, ledger_path=ledger_path) == []


def test_cli_tail_prints_last_n(ledger_path: Path, capsys) -> None:
    for i in range(1, 8):
        veto_ledger.record_veto(f"T-{i}", "s", f"r{i}", ledger_path=ledger_path)
    rc = veto_ledger.main(["--tail", "3", "--path", str(ledger_path)])
    assert rc == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert [json.loads(line)["trade_id"] for line in out] == ["T-5", "T-6", "T-7"]


def test_cli_tail_default_is_5(ledger_path: Path, capsys) -> None:
    for i in range(1, 10):
        veto_ledger.record_veto(f"T-{i}", "s", f"r{i}", ledger_path=ledger_path)
    rc = veto_ledger.main(["--path", str(ledger_path)])
    assert rc == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 5


def test_cli_script_executes(ledger_path: Path) -> None:
    veto_ledger.record_veto("T-CLI", "s", "r", ledger_path=ledger_path)
    repo_root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "bin" / "vetoes"), "--tail", "1", "--path", str(ledger_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout.strip())["trade_id"] == "T-CLI"
