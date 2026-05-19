#!/usr/bin/env python3
"""Render an SVG equity curve from a JSONL ledger emitted by OnData.

Usage:
  python scripts/plot_equity.py logs/equity.jsonl --out equity.svg
  python scripts/plot_equity.py logs/equity.jsonl --out equity.svg --width 960 --height 320

The JSONL schema is one bar per line: {"time": iso8601, "equity": float, "cash": float}.
Lines that fail to parse or lack a numeric `equity` are skipped.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape


def load_points(jsonl_path: Path) -> list[tuple[str, float]]:
    points: list[tuple[str, float]] = []
    with jsonl_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                equity = float(record["equity"])
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
            time = str(record.get("time", ""))
            points.append((time, equity))
    return points


def render_svg(points: list[tuple[str, float]], width: int, height: int) -> str:
    pad = 24
    if not points:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">'
            f'<rect width="{width}" height="{height}" fill="#0b1020"/>'
            f'<text x="{width // 2}" y="{height // 2}" fill="#cbd5f5" '
            f'font-family="monospace" font-size="14" text-anchor="middle">no equity data</text>'
            f"</svg>"
        )

    equities = [eq for _, eq in points]
    lo, hi = min(equities), max(equities)
    span = hi - lo if hi > lo else 1.0
    n = len(points)
    x_step = (width - 2 * pad) / max(n - 1, 1)

    coords = []
    for i, (_, eq) in enumerate(points):
        x = pad + i * x_step
        y = height - pad - ((eq - lo) / span) * (height - 2 * pad)
        coords.append(f"{x:.2f},{y:.2f}")
    polyline = " ".join(coords)

    first_t = escape(points[0][0])
    last_t = escape(points[-1][0])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        f'<rect width="{width}" height="{height}" fill="#0b1020"/>'
        f'<polyline fill="none" stroke="#7dd3fc" stroke-width="2" points="{polyline}"/>'
        f'<text x="{pad}" y="{pad - 6}" fill="#cbd5f5" font-family="monospace" font-size="11">'
        f'equity {lo:.2f} -> {hi:.2f} ({n} bars)</text>'
        f'<text x="{pad}" y="{height - 6}" fill="#94a3b8" font-family="monospace" font-size="10">'
        f'{first_t}</text>'
        f'<text x="{width - pad}" y="{height - 6}" fill="#94a3b8" font-family="monospace" font-size="10" '
        f'text-anchor="end">{last_t}</text>'
        f"</svg>"
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render an SVG equity curve from JSONL.")
    parser.add_argument("input", help="Path to equity.jsonl")
    parser.add_argument("--out", required=True, help="Output SVG path")
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=240)
    args = parser.parse_args(list(argv) if argv is not None else None)

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"plot_equity: input not found: {in_path}", file=sys.stderr)
        return 2

    points = load_points(in_path)
    svg = render_svg(points, args.width, args.height)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg, encoding="utf-8")
    print(f"wrote {out_path} ({len(points)} points)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
