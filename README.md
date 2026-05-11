# tradingbot

QuantConnect equities strategy using a static or fundamental-filtered universe,
technical entry signals, position sizing, and explicit stop-loss / take-profit
targets.

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
