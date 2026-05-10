# tradingbot

> quantConnect algorithm combining EMA crossovers, fundamental filtering, and Kelly position sizing.

[![License](https://img.shields.io/github/license/wranngle/tradingbot?color=A371F7)](./LICENSE) ![Status](https://img.shields.io/badge/status-experimental-orange.svg)

> [!NOTE]
> Experiment. Built to learn one specific thing. Code may not survive.

## What it does

This algorithm evaluates equities on the QuantConnect platform using a mix of technical and fundamental factors. It filters the trading universe by price, P/E, revenue growth, and market cap. Entry and exit decisions rely on EMA crossovers, MACD, RSI, Stochastic, and ATR breakouts. It manages risk with dynamic stop-loss levels, sector and portfolio caps, and Kelly-criterion position sizing while remaining aware of the Pattern Day Trader (PDT) rule.

## Usage

This code relies on the `AlgorithmImports` module injected by QuantConnect at runtime. It does not run as a standalone Python script.

1. Create a project via the QuantConnect dashboard or the `lean` CLI.
2. Copy the Python files from this repository into the project root.
3. Edit `config.py` to set your backtest dates, starting cash, condition flags, and parameter values.
4. Run your backtest.

To exercise the decision logic and price-target math locally without the QuantConnect engine:

```bash
pip install pytest
pytest
```

## License

See [LICENSE](./LICENSE).
