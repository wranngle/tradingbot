# tradingbot

A multi-factor equity trading algorithm built for the [QuantConnect](https://www.quantconnect.com/) platform. It combines technical indicators (EMA crossovers, MACD, RSI, Stochastic, ATR breakouts), fundamental universe filtering (price, P/E, revenue growth, market cap), and risk-management rules (ATR / Fibonacci / trailing / fixed stop-loss and take-profit, Kelly-criterion position sizing, sector and portfolio caps, PDT-rule awareness).

## Demo

🎬 _Loom walkthrough coming soon — backtest dashboard + risk-control behavior._

<!-- Replace with: <a href="https://www.loom.com/share/<id>"><img src="https://cdn.loom.com/sessions/thumbnails/<id>-with-play.gif" alt="Tradingbot demo"></a> -->

> **Disclaimer:** This code is shared for educational and research purposes only. It is **not** financial advice and comes with **no warranty of profitability or correctness** (see `LICENSE`). Do not run it with real money without thoroughly understanding, testing, and modifying it for your own situation. Past backtest performance does not guarantee future results.

## Layout

| File | Purpose |
| --- | --- |
| `main.py` | `QCAlgorithm` entry point; wires up event handlers. |
| `config.py` | All tunable conditions and parameters. |
| `variables.py` | Shared mutable state across handlers. |
| `AddUniverse.py` | Static or dynamic (fundamentals-filtered) universe selection. |
| `OnSecuritiesChanged.py` | Initializes indicators and consolidators when symbols enter/leave the universe. |
| `OnWarmupFinished.py` | Logs the post-warmup universe snapshot. |
| `OnData.py` | Per-bar logic: evaluates buy/sell, places orders, cancels stale ones. |
| `OnOrderEvent.py` | Order fill bookkeeping: sector aggregates, day-trade counter, Kelly stats. |
| `shouldBuy.py` / `shouldSell.py` | Buy / sell decision logic. |
| `calculateStopLossPrice.py` / `calculateTakeProfitPrice.py` | Price-target math. |
| `sectorAnalysis.py` | Sector-level portfolio aggregation helpers. |
| `charts.py` | Persists indicator and position-size snapshots to the QC Object Store. |
| `research.ipynb` | Scratch notebook for QC Research. |

## Running

This project is designed to run inside QuantConnect (cloud or `lean` CLI). It depends on the `AlgorithmImports` module that QC injects at runtime; it cannot run as a plain Python script.

1. Create a project in the [QC dashboard](https://www.quantconnect.com/) or with the [`lean` CLI](https://www.quantconnect.com/docs/v2/lean-cli/installation/installing-lean-cli).
2. Copy these files into the project root.
3. Adjust `config.py` to taste (start/end dates, starting cash, condition flags, parameter values).
4. Run a backtest.

## Testing

Unit tests live under `tests/` and run with `pytest`. They stub the QuantConnect-only `AlgorithmImports` module so the pure logic (price-target math, decision functions, universe filtering) can be exercised locally:

```bash
pip install pytest
pytest
```

Coverage is currently minimal — see `tests/conftest.py` for the QC stubs and `tests/README.md` for the priority list of areas still to cover.

## QuantConnect docs

<https://www.quantconnect.com/docs/v2/writing-algorithms>
