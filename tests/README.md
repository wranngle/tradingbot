# tests/

Local pytest suite. Stubs `AlgorithmImports` (the QuantConnect runtime) so
pure-logic modules can be exercised without the QC backtest harness.

## Run

```bash
pip install pytest
pytest
```

## What's covered

- `calculateStopLossPrice` — branch coverage on each enabled stop-loss method,
  disabled-method handling, and nearest-retracement Fibonacci math.
- `calculateTakeProfitPrice` — ATR direction, enabled-method selection, and
  disabled-method handling.
- `shouldBuy` — disabled buy conditions do not block enabled ones, empty Kelly
  history does not force zero-share startup, PDT gating blocks when enabled,
  and the portfolio-value buy floor is enforced.
- `shouldSell` — pins down the `=` vs `==` regression and the tuple return
  contract.
- `AddUniverse` — static ticker strings register cleanly, and malformed
  fundamentals do not empty the dynamic universe.
- `sectorAnalysis` — sector aggregation recomputes instead of accumulating
  stale values.
- `OnOrderEvent` — sell-fill profit uses absolute sold quantity so winning
  exits do not count as losses.
- `OnData` — invested symbols skip buy recalculation so existing sell targets
  do not chase current price, and stale tickets are removed after cancellation.
- `OnSecuritiesChanged` — one consolidator per symbol fans out to all
  indicators.

## What's NOT yet covered (priority order)

1. **`OnOrderEvent` Kelly-criterion math** — broaden the current happy-path
   test to cover mixed win/loss sequences and day-trade de-duplication.
2. **`AddUniverse.filterAndSortUniverse`** — pure data pipeline over a list
   of fundamental fixtures. Verify each filter, the sort/slice chain
   (top-100 dollar-volume → top-50 P/E → bottom-10 market-cap), and the
   blacklist/min-price disabled paths.
3. **`OnSecuritiesChanged`** — indicator/consolidator registration and
   removal lifecycle.
4. **`OnData` order submission branches** — add fixtures for buy limit orders,
   partial take-profit exits, and full liquidation exits.

## Adding new tests

Use the `reset_variables`, `fake_symbol`, and `fake_algorithm` fixtures from
`conftest.py`. Extend the `AlgorithmImports` stub there if a new test needs
an indicator or QC type that isn't yet exposed.
