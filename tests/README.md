# tests/

Local pytest suite. Stubs `AlgorithmImports` (the QuantConnect runtime) so
pure-logic modules can be exercised without the QC backtest harness.

## Run

```bash
pip install pytest
pytest
```

## What's covered

- `calculateStopLossPrice` — branch coverage on each enabled stop-loss method
  plus the `"Disabled"` regression.
- `shouldSell` — pins down the `=` vs `==` regression and the tuple return
  contract.

## What's NOT yet covered (priority order)

1. **`shouldBuy.py`** — by far the largest function in the codebase. Needs a
   matrix of tests toggling each `c.buy_condition_*` flag and checking
   position-size selection, the risk/reward early-exit, and the order-tag
   payload shape.
2. **`calculateTakeProfitPrice.py`** — same shape as the stop-loss tests.
   Mostly covered by analogy but worth its own file.
3. **`OnOrderEvent` Kelly-criterion math** — verify `win_probability`,
   `win_loss_ratio`, and `kelly_criterion` are recomputed correctly across
   a sequence of fills. (The current formula has a suspicious
   `if v.win_loss_ratio != 0 else float('inf')` check on the just-assigned
   variable — needs a product-side decision before testing.)
4. **`AddUniverse.filterAndSortUniverse`** — pure data pipeline over a list
   of fundamental fixtures. Verify each filter, the sort/slice chain
   (top-100 dollar-volume → top-50 P/E → bottom-10 market-cap), and the
   blacklist/min-price disabled paths.
5. **`sectorAnalysis`** — sector aggregation, plus the `+=` accumulator in
   `calculatePortfolioValueForSector` (currently never zeros prior values,
   so repeated calls double-count).
6. **`OnSecuritiesChanged`** — indicator/consolidator registration and
   removal lifecycle.
7. **`OnData.CancelOldOrders`** — the `order_age % 15 == 0` check on a float
   will essentially never be true; worth a test that demonstrates the
   intended behavior so it can be fixed.

## Adding new tests

Use the `reset_variables`, `fake_symbol`, and `fake_algorithm` fixtures from
`conftest.py`. Extend the `AlgorithmImports` stub there if a new test needs
an indicator or QC type that isn't yet exposed.
