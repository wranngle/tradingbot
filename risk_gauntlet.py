"""Pre-flight risk gauntlet.

Blocks any strategy load whose config exceeds hardcoded risk caps so unsafe
configurations never reach a backtest or live run.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


MAX_DRAWDOWN_CAP = 0.30
LEVERAGE_CAP = 2.0
POSITION_CONCENTRATION_CAP = 0.20


class RiskGauntletError(Exception):
    def __init__(self, cap_name: str, actual_value: float, allowed_value: float) -> None:
        self.cap_name = cap_name
        self.actual_value = actual_value
        self.allowed_value = allowed_value
        super().__init__(
            f"risk gauntlet: {cap_name} violated (actual={actual_value}, allowed<={allowed_value})"
        )


@dataclass(frozen=True)
class _Check:
    cap_name: str
    attr: str
    allowed: float


_CHECKS: tuple[_Check, ...] = (
    _Check("max_drawdown_cap", "max_drawdown_pct", MAX_DRAWDOWN_CAP),
    _Check("leverage_cap", "leverage", LEVERAGE_CAP),
    _Check("position_concentration_cap", "max_position_pct", POSITION_CONCENTRATION_CAP),
)


class RiskGauntlet:
    def validate(self, config: Any) -> None:
        for check in _CHECKS:
            actual = getattr(config, check.attr)
            if actual > check.allowed:
                raise RiskGauntletError(check.cap_name, actual, check.allowed)
