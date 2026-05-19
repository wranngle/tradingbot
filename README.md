# tradingbot

A risk-first algorithmic trading lab. Strategies move through explicit
**lifecycle stages** (`local → paper → live`) and must clear a pre-flight
**risk gauntlet** — drawdown cap, leverage cap, position concentration cap —
before any backtest or deployment runs. The point of this repo is not to
maximize returns; it is to make unsafe configurations unrunnable.

## Risk gauntlet

Every algorithm load is gated by a pre-flight check that validates the
strategy config against three hardcoded caps:

- **Max drawdown** — refuse if `config.max_drawdown_pct > 0.30`.
- **Leverage** — refuse if `config.leverage > 2.0`.
- **Position concentration** — refuse if `config.max_position_pct > 0.20`.

Violations raise `RiskGauntletError(cap_name, actual, allowed)` before any
order, indicator, or universe selection is touched. The cap values are
deliberately hardcoded in the gauntlet — the gauntlet is the boundary, not a
preference.

## Lifecycle stages

Strategies are tagged with a `stage` in `strategy.yaml`:

| Stage | Notional cap | Purpose |
|---|---|---|
| `local` | $0 (paper, local stub) | Develop logic, run pytest, replay black-swan fixtures. |
| `paper` | exchange paper account | Forward-test against live market data, no real money. |
| `live` | per-strategy `notional_cap` | Promoted only when paper-stage promotion criteria are met. |

Promotion is not automatic. The strategy YAML records the criteria; the
operator decides when to flip the stage.

## Usage

This project expects QuantConnect's `AlgorithmImports` runtime. It is not a
standalone script.

1. Create a QuantConnect project in the dashboard or with the `lean` CLI.
2. Copy these Python files into the project root.
3. Edit `config.py` for dates, cash, universe, and strategy flags.
4. Run the backtest.

Local logic tests use a small QuantConnect stub:

```bash
pip install pytest
pytest
```

## License

See [LICENSE](./LICENSE).
