"""Daily risk-state digest.

Reads a JSON snapshot of the trading bot's current risk state and emits a
deterministic markdown digest with four sections: drawdown, regime,
gauntlet history, and exposure by asset.

Inputs are JSON, not live module calls, so the digest stays auditable
outside the QuantConnect runtime and works alongside the round-1 modules
(``risk_gauntlet.py``, ``regime.py``, ``strategy.yaml`` lifecycle) without
duplicating their logic — those modules feed the snapshot, this module
renders it.

Schema (``fixtures/digest_input.json`` is the canonical example)::

    {
      "as_of": "2026-05-14",
      "current_drawdown_pct": 0.082,
      "max_drawdown_cap": 0.30,
      "regime": "choppy",
      "gauntlet_history": [
        {"date": "2026-05-08", "outcome": "pass", "strategy": "core"},
        {"date": "2026-05-09", "outcome": "veto",
         "strategy": "experimental", "reason": "leverage_cap"}
      ],
      "exposure_by_asset": {"SPY": 0.42, "QQQ": 0.18, "CASH": 0.40}
    }

Any missing field renders as a ``no data`` placeholder so a fresh deployment
still produces a valid digest.

Usage::

    python risk_digest.py --input fixtures/digest_input.json
    python risk_digest.py --input fixtures/digest_input.json --out out/digest.md

Determinism is guaranteed: rows are sorted (gauntlet by date ascending,
exposures by asset symbol ascending) so the same input bytes produce the
same output bytes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

_NO_DATA = "_no data_"
_SECTIONS = (
    "## Drawdown",
    "## Regime",
    "## Gauntlet history (last 7d)",
    "## Exposure by asset",
)


def build_digest(state: Mapping[str, Any]) -> str:
    """Render a risk-state snapshot as deterministic markdown."""
    parts: list[str] = []
    as_of = state.get("as_of")
    header = f"# Daily risk digest{f' — {as_of}' if as_of else ''}"
    parts.append(header)
    parts.append("")
    parts.append(_drawdown_section(state))
    parts.append("")
    parts.append(_regime_section(state))
    parts.append("")
    parts.append(_gauntlet_section(state.get("gauntlet_history")))
    parts.append("")
    parts.append(_exposure_section(state.get("exposure_by_asset")))
    parts.append("")
    return "\n".join(parts)


def _drawdown_section(state: Mapping[str, Any]) -> str:
    current = state.get("current_drawdown_pct")
    cap = state.get("max_drawdown_cap")
    lines = ["## Drawdown", ""]
    if current is None and cap is None:
        lines.append(_NO_DATA)
        return "\n".join(lines)
    lines.append("| metric | value |")
    lines.append("| --- | --- |")
    lines.append(f"| current | {_pct(current)} |")
    lines.append(f"| cap | {_pct(cap)} |")
    if isinstance(current, (int, float)) and isinstance(cap, (int, float)) and cap > 0:
        headroom = max(cap - float(current), 0.0)
        lines.append(f"| headroom | {_pct(headroom)} |")
    return "\n".join(lines)


def _regime_section(state: Mapping[str, Any]) -> str:
    regime = state.get("regime")
    lines = ["## Regime", ""]
    if not regime:
        lines.append(_NO_DATA)
        return "\n".join(lines)
    lines.append(f"Current: **{regime}**")
    confidence = state.get("regime_confidence")
    if isinstance(confidence, (int, float)):
        lines.append("")
        lines.append(f"Confidence: {float(confidence):.2f}")
    return "\n".join(lines)


def _gauntlet_section(history: Any) -> str:
    lines = ["## Gauntlet history (last 7d)", ""]
    if not isinstance(history, Sequence) or not history:
        lines.append(_NO_DATA)
        return "\n".join(lines)
    rows = sorted(
        (
            {
                "date": str(entry.get("date", "")),
                "strategy": str(entry.get("strategy", "")),
                "outcome": str(entry.get("outcome", "")),
                "reason": str(entry.get("reason", "")),
            }
            for entry in history
            if isinstance(entry, Mapping)
        ),
        key=lambda r: (r["date"], r["strategy"], r["outcome"]),
    )
    if not rows:
        lines.append(_NO_DATA)
        return "\n".join(lines)
    lines.append("| date | strategy | outcome | reason |")
    lines.append("| --- | --- | --- | --- |")
    for row in rows:
        lines.append(
            f"| {row['date'] or '-'} | {row['strategy'] or '-'} | "
            f"{row['outcome'] or '-'} | {row['reason'] or '-'} |"
        )
    return "\n".join(lines)


def _exposure_section(exposure: Any) -> str:
    lines = ["## Exposure by asset", ""]
    if not isinstance(exposure, Mapping) or not exposure:
        lines.append(_NO_DATA)
        return "\n".join(lines)
    rows = sorted(exposure.items(), key=lambda kv: kv[0])
    lines.append("| asset | weight |")
    lines.append("| --- | --- |")
    for asset, weight in rows:
        lines.append(f"| {asset} | {_pct(weight)} |")
    return "\n".join(lines)


def _pct(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "-"
    return f"{float(value) * 100:.2f}%"


def _load_state(path: Path) -> Mapping[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="risk-digest",
        description="Render a daily risk-state digest from a JSON snapshot.",
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="path to a JSON snapshot of the risk state",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output file (stdout if omitted)",
    )
    args = parser.parse_args(argv)
    state = _load_state(args.input)
    digest = build_digest(state)
    if args.out is None:
        sys.stdout.write(digest)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(digest, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
