"""Test setup: stub the QuantConnect runtime so modules can be imported locally.

Every source file does `from AlgorithmImports import *`, which only exists
inside QuantConnect. We register a fake module on `sys.modules` before any
project module is imported so pytest collection succeeds.

The stubs are intentionally minimal — just enough to satisfy `import *` and
to let tests construct fake `algorithm`, `Portfolio`, indicator, and data
objects via `unittest.mock`. Add more attributes here as new tests need them.
"""

from __future__ import annotations

import sys
import types
from collections import deque
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _install_algorithm_imports_stub() -> None:
    if "AlgorithmImports" in sys.modules:
        return

    module = types.ModuleType("AlgorithmImports")

    class _Enum:
        def __init__(self, name: str) -> None:
            self.name = name

        def __repr__(self) -> str:
            return f"<{type(self).__name__}.{self.name}>"

    class Resolution:
        Daily = _Enum("Daily")
        Hour = _Enum("Hour")
        Minute = _Enum("Minute")
        Second = _Enum("Second")
        Tick = _Enum("Tick")

    class MovingAverageType:
        Wilders = _Enum("Wilders")
        Simple = _Enum("Simple")
        Exponential = _Enum("Exponential")

    class BrokerageName:
        TradierBrokerage = _Enum("TradierBrokerage")
        InteractiveBrokersBrokerage = _Enum("InteractiveBrokersBrokerage")

    class AccountType:
        Cash = _Enum("Cash")
        Margin = _Enum("Margin")

    class OrderDirection:
        Buy = _Enum("Buy")
        Sell = _Enum("Sell")
        Hold = _Enum("Hold")

    class OrderStatus:
        Submitted = _Enum("Submitted")
        Filled = _Enum("Filled")
        Canceled = _Enum("Canceled")
        Invalid = _Enum("Invalid")
        PartiallyFilled = _Enum("PartiallyFilled")

    # Indicator placeholder classes — tests should mock the instances.
    class _IndicatorStub:
        def __init__(self, *args, **kwargs):
            self.Current = MagicMock(Value=0)
            self.Previous = MagicMock(Value=0)
            self.IsReady = True

        def Update(self, *_args, **_kwargs):
            return None

    class AverageTrueRange(_IndicatorStub): ...
    class ExponentialMovingAverage(_IndicatorStub): ...
    class MovingAverageConvergenceDivergence(_IndicatorStub):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.Signal = MagicMock(Current=MagicMock(Value=0))
    class RelativeStrengthIndex(_IndicatorStub): ...
    class Stochastic(_IndicatorStub): ...
    class Minimum(_IndicatorStub): ...

    class _BarStub: ...
    class TradeBar(_BarStub): ...
    class QuoteBar(_BarStub): ...
    class IndicatorDataPoint(_BarStub):
        def __init__(self, end_time=None, value=0):
            self.EndTime = end_time
            self.Value = value

    class Symbol:
        def __init__(self, ticker: str = "STUB"):
            self.Value = ticker

        def to_dict(self):
            return {"Symbol": self.Value}

        def __str__(self):
            return self.Value

        def __hash__(self):
            return hash(self.Value)

        def __eq__(self, other):
            return isinstance(other, Symbol) and self.Value == other.Value

    class Fundamental: ...

    class IndicatorBase:
        def __class_getitem__(cls, _item):
            return cls

    class QCAlgorithm:
        """Bare-bones base class so subclasses can be instantiated in tests."""

    # Expose names for `from AlgorithmImports import *`.
    for name, obj in list(locals().items()):
        if name.startswith("_") or name == "module":
            continue
        setattr(module, name, obj)

    module.List = list
    module.__all__ = [
        "Resolution", "MovingAverageType", "BrokerageName", "AccountType",
        "OrderDirection", "OrderStatus",
        "AverageTrueRange", "ExponentialMovingAverage",
        "MovingAverageConvergenceDivergence", "RelativeStrengthIndex",
        "Stochastic", "Minimum",
        "TradeBar", "QuoteBar", "IndicatorDataPoint", "IndicatorBase",
        "Symbol", "Fundamental", "QCAlgorithm", "List",
    ]
    sys.modules["AlgorithmImports"] = module


_install_algorithm_imports_stub()


@pytest.fixture
def reset_variables():
    """Reset the shared mutable state in `variables.py` between tests.

    The project keeps per-symbol state in module-level dicts. Without this
    fixture, tests bleed state into each other.
    """
    import variables as v

    snapshots = {}
    for attr in dir(v):
        if attr.startswith("_"):
            continue
        value = getattr(v, attr)
        if isinstance(value, (dict, set, list, deque)):
            snapshots[attr] = deque(maxlen=value.maxlen) if isinstance(value, deque) else type(value)()
            setattr(v, attr, snapshots[attr])
    yield v


@pytest.fixture
def fake_symbol():
    from AlgorithmImports import Symbol
    return Symbol("AAPL")


@pytest.fixture
def fake_algorithm():
    """A MagicMock-based stand-in for a `QCAlgorithm` instance.

    Configure `Portfolio`, `Securities`, `Time`, etc. per-test as needed.
    """
    algo = MagicMock(name="algorithm")
    algo.Portfolio = MagicMock()
    algo.Portfolio.Cash = 10_000
    algo.Portfolio.TotalPortfolioValue = 10_000
    algo.Securities = {}
    algo.Transactions = MagicMock()
    return algo
