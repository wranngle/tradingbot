"""Tests for security lifecycle wiring."""

from unittest.mock import MagicMock


class _EventHook:
    def __init__(self):
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self


def test_symbol_gets_one_consolidator_for_all_indicators(reset_variables, fake_symbol):
    import variables as v
    from OnSecuritiesChanged import OnSecuritiesChangedHandler

    consolidator = MagicMock()
    consolidator.DataConsolidated = _EventHook()

    algo = MagicMock()
    algo.ResolveConsolidator.return_value = consolidator

    handler = OnSecuritiesChangedHandler(algo)
    handler.ensureSymbolInitialized(fake_symbol)

    assert fake_symbol in v.active_symbols
    assert len(v.indicators[fake_symbol]) == 7
    assert v.consolidators[fake_symbol] == [consolidator]
    algo.SubscriptionManager.AddConsolidator.assert_called_once_with(
        fake_symbol,
        consolidator,
    )
    assert len(consolidator.DataConsolidated.handlers) == 1
