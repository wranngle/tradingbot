"""Drawdown-breach alarm webhook.

Reads a risk-state snapshot (same shape as risk_digest fixtures: a JSON
dict with `current_drawdown_pct` and optional `strategy`, `regime`,
`asof`). Compares the current drawdown against a tier table and, when
the highest-severity tier is exceeded, POSTs a JSON payload to a Slack-
or Discord-compatible webhook URL.

Decision is pure (`evaluate`) so it is trivially testable in isolation;
network IO is isolated to `_post` which the CLI calls.

Stdlib only. The HTTP call uses `urllib.request.urlopen`. Tests stub it
at the module-level seam `tradingbot_alarm_post` (re-exported from
`_post`) so they remain decoupled from the urllib internals.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_TIERS: tuple[tuple[str, float], ...] = (
    ("info", 5.0),
    ("warn", 10.0),
    ("critical", 20.0),
)


@dataclass(frozen=True)
class Evaluation:
    breach: bool
    tier: str | None
    threshold_pct: float | None
    drawdown_pct: float
    strategy: str | None = None
    regime: str | None = None
    asof: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def payload(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "breach": self.breach,
            "drawdown_pct": self.drawdown_pct,
            "tier": self.tier,
            "threshold_pct": self.threshold_pct,
            "strategy": self.strategy,
            "regime": self.regime,
            "asof": self.asof,
        }
        if self.extra:
            body["extra"] = dict(self.extra)
        body["text"] = self._slack_text()
        return body

    def _slack_text(self) -> str:
        if not self.breach:
            return f"OK — drawdown {self.drawdown_pct:.2f}% within all tiers"
        who = self.strategy or "portfolio"
        return (
            f"[{(self.tier or '').upper()}] {who} drawdown "
            f"{self.drawdown_pct:.2f}% breached "
            f"{self.threshold_pct:.2f}% tier"
        )


def evaluate(
    snapshot: dict[str, Any],
    tiers: tuple[tuple[str, float], ...] = DEFAULT_TIERS,
) -> Evaluation:
    if "current_drawdown_pct" not in snapshot:
        raise ValueError("snapshot missing 'current_drawdown_pct'")
    drawdown = float(snapshot["current_drawdown_pct"])
    if drawdown < 0:
        raise ValueError("drawdown must be expressed as a non-negative percent")

    ordered = sorted(tiers, key=lambda item: item[1])
    matched: tuple[str, float] | None = None
    for name, threshold in ordered:
        if drawdown >= threshold:
            matched = (name, threshold)

    extra = {
        key: snapshot[key]
        for key in snapshot
        if key
        not in {"current_drawdown_pct", "strategy", "regime", "asof"}
    }
    return Evaluation(
        breach=matched is not None,
        tier=matched[0] if matched else None,
        threshold_pct=matched[1] if matched else None,
        drawdown_pct=drawdown,
        strategy=snapshot.get("strategy"),
        regime=snapshot.get("regime"),
        asof=snapshot.get("asof"),
        extra=extra,
    )


def _post(url: str, payload: dict[str, Any], timeout: float = 5.0) -> int:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return int(getattr(response, "status", 200))


def fire(
    snapshot: dict[str, Any],
    url: str,
    *,
    tiers: tuple[tuple[str, float], ...] = DEFAULT_TIERS,
    only_on_breach: bool = True,
    poster=None,
    timeout: float = 5.0,
) -> tuple[Evaluation, bool]:
    evaluation = evaluate(snapshot, tiers=tiers)
    if only_on_breach and not evaluation.breach:
        return evaluation, False
    send = poster or _post
    send(url, evaluation.payload(), timeout=timeout)
    return evaluation, True


def _load_snapshot(path: str) -> dict[str, Any]:
    if path == "-":
        return json.loads(sys.stdin.read())
    text = Path(path).read_text(encoding="utf-8")
    return json.loads(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="alarm",
        description="Drawdown-breach webhook for Slack/Discord.",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to risk-state snapshot JSON ('-' for stdin).",
    )
    parser.add_argument(
        "--url",
        help="Webhook URL. Falls back to $ALARM_WEBHOOK_URL.",
    )
    parser.add_argument(
        "--always",
        action="store_true",
        help="POST even when no tier breached (default: only on breach).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the would-be payload to stdout; no network call.",
    )
    args = parser.parse_args(argv)

    url = args.url or os.environ.get("ALARM_WEBHOOK_URL")
    snapshot = _load_snapshot(args.input)
    evaluation = evaluate(snapshot)
    payload = evaluation.payload()

    if args.dry_run:
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return 0

    if not evaluation.breach and not args.always:
        sys.stdout.write(json.dumps({"breach": False, "posted": False}) + "\n")
        return 0

    if not url:
        sys.stderr.write(
            "alarm: --url or $ALARM_WEBHOOK_URL is required to POST\n"
        )
        return 2

    try:
        _post(url, payload)
    except urllib.error.URLError as err:
        sys.stderr.write(f"alarm: webhook POST failed: {err}\n")
        return 1

    sys.stdout.write(
        json.dumps({"breach": evaluation.breach, "posted": True}) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
