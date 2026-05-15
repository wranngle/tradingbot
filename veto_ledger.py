"""Per-trade veto ledger.

Append-only JSONL log of every trade rejected by upstream risk checks
(gauntlet, position-cap, etc.). Each record captures `trade_id`,
`strategy`, `reason`, `timestamp` so post-mortems can answer "why didn't
we take that trade?" without rebuilding state from logs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

DEFAULT_LEDGER_PATH = Path(os.environ.get("VETO_LEDGER_PATH", "logs/vetoes.jsonl"))


def record_veto(
    trade_id: str,
    strategy: str,
    reason: str,
    *,
    ledger_path: Path | str | None = None,
    timestamp: str | None = None,
) -> dict:
    """Append a veto record to the JSONL ledger and return the row.

    `timestamp` defaults to UTC now in ISO-8601. The parent directory is
    created if missing so callers do not need to pre-stage `logs/`.
    """
    path = Path(ledger_path) if ledger_path is not None else DEFAULT_LEDGER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "trade_id": str(trade_id),
        "strategy": str(strategy),
        "reason": str(reason),
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def tail(n: int = 5, ledger_path: Path | str | None = None) -> list[dict]:
    """Return the last `n` veto records (oldest-first) from the ledger."""
    if n <= 0:
        return []
    path = Path(ledger_path) if ledger_path is not None else DEFAULT_LEDGER_PATH
    if not path.exists():
        return []
    keep: deque[dict] = deque(maxlen=n)
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                keep.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return list(keep)


def veto_if(
    predicate_failed: bool,
    *,
    trade_id: str,
    strategy: str,
    reason: str,
    ledger_path: Path | str | None = None,
) -> bool:
    """Hook helper: when `predicate_failed` is True, record and return True.

    Returns True if the trade was vetoed (and the caller should skip it),
    False if the trade may proceed. Callers wire this in place of inline
    rejection logic so every veto reaches the ledger.
    """
    if predicate_failed:
        record_veto(trade_id, strategy, reason, ledger_path=ledger_path)
        return True
    return False


def _format(records: Iterable[dict]) -> str:
    return "\n".join(json.dumps(r, sort_keys=True) for r in records)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vetoes", description="Inspect the per-trade veto ledger")
    parser.add_argument("--tail", type=int, default=5, help="show the last N vetoes (default 5)")
    parser.add_argument("--path", default=None, help="ledger path override")
    args = parser.parse_args(argv)
    records = tail(args.tail, ledger_path=args.path)
    if not records:
        return 0
    sys.stdout.write(_format(records) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
