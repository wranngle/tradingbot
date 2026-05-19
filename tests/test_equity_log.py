"""Tests for the equity-curve JSONL emit + SVG plot pipeline."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock


def _make_algo(time):
    algo = MagicMock()
    algo.IsWarmingUp = False
    algo.Portfolio = MagicMock()
    algo.Portfolio.TotalPortfolioValue = 100_000.0
    algo.Portfolio.Cash = 50_000.0
    algo.Time = time
    return algo


def test_emit_equity_bar_writes_one_jsonl_line(tmp_path):
    from OnData import emit_equity_bar

    log_path = tmp_path / "equity.jsonl"
    algo = _make_algo(datetime(2024, 1, 1, 9, 30))
    algo.Portfolio.TotalPortfolioValue = 123_456.78
    algo.Portfolio.Cash = 1_000.0

    emit_equity_bar(algo, path=str(log_path))

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["equity"] == 123_456.78
    assert record["cash"] == 1_000.0
    assert record["time"].startswith("2024-01-01T09:30")


def test_emit_equity_bar_appends_at_least_100_lines_for_100_bars(tmp_path):
    from OnData import emit_equity_bar

    log_path = tmp_path / "equity.jsonl"
    start = datetime(2024, 1, 1, 9, 30)

    for i in range(100):
        algo = _make_algo(start + timedelta(minutes=i))
        algo.Portfolio.TotalPortfolioValue = 100_000.0 + i * 12.5
        emit_equity_bar(algo, path=str(log_path))

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 100
    first = json.loads(lines[0])
    last = json.loads(lines[-1])
    assert first["equity"] == 100_000.0
    assert last["equity"] == 100_000.0 + 99 * 12.5


def test_plot_equity_script_writes_valid_svg(tmp_path):
    log_path = tmp_path / "equity.jsonl"
    svg_path = tmp_path / "equity.svg"

    with log_path.open("w", encoding="utf-8") as fh:
        for i in range(100):
            fh.write(
                json.dumps(
                    {
                        "time": f"2024-01-01T09:{30 + i // 60:02d}:{i % 60:02d}",
                        "equity": 100_000.0 + i * 7.5,
                        "cash": 50_000.0,
                    }
                )
                + "\n"
            )

    script = Path(__file__).resolve().parent.parent / "scripts" / "plot_equity.py"
    result = subprocess.run(
        [sys.executable, str(script), str(log_path), "--out", str(svg_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    svg = svg_path.read_text(encoding="utf-8")
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert 'xmlns="http://www.w3.org/2000/svg"' in svg
    assert "<polyline" in svg


def test_plot_equity_handles_empty_jsonl(tmp_path):
    log_path = tmp_path / "equity.jsonl"
    log_path.write_text("", encoding="utf-8")
    svg_path = tmp_path / "equity.svg"

    script = Path(__file__).resolve().parent.parent / "scripts" / "plot_equity.py"
    result = subprocess.run(
        [sys.executable, str(script), str(log_path), "--out", str(svg_path)],
        check=True,
        capture_output=True,
        text=True,
    )

    svg = svg_path.read_text(encoding="utf-8")
    assert svg.startswith("<svg")
    assert "no equity data" in svg
