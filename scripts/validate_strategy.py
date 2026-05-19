"""Validate strategy.yaml against the lifecycle schema.

Usage:
    python scripts/validate_strategy.py [path/to/strategy.yaml]

Exits 0 with a one-line OK summary on success, 1 with a pydantic error on failure.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator


class PromotionCriteria(BaseModel):
    min_paper_trades: int = Field(ge=1)
    min_sharpe: float = Field(ge=0.0)
    max_drawdown_pct: float = Field(gt=0.0, le=1.0)
    min_paper_days: int = Field(ge=1)


class Strategy(BaseModel):
    stage: Literal["local", "paper", "live"]
    notional_cap: float = Field(gt=0)
    promotion_criteria: PromotionCriteria
    version: str

    @field_validator("version")
    @classmethod
    def _semver_shape(cls, v: str) -> str:
        parts = v.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ValueError("version must be MAJOR.MINOR.PATCH (numeric)")
        return v


def load_strategy(path: Path) -> Strategy:
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, dict):
        raise ValueError(f"strategy YAML root must be a mapping, got {type(raw).__name__}")
    return Strategy(**raw)


def main(argv: list[str]) -> int:
    target = Path(argv[1]) if len(argv) > 1 else Path("strategy.yaml")
    if not target.exists():
        print(f"strategy file not found: {target}", file=sys.stderr)
        return 1
    try:
        strategy = load_strategy(target)
    except (ValidationError, ValueError, yaml.YAMLError) as exc:
        print(f"strategy validation failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"OK stage={strategy.stage} notional_cap={strategy.notional_cap} "
        f"version={strategy.version}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
