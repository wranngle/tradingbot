# tradingbot

> a quantConnect equities algorithm combining technical indicators and Kelly position sizing.

[![License](https://img.shields.io/github/license/wranngle/tradingbot?color=A371F7)](./LICENSE) ![Status](https://img.shields.io/badge/status-active-brightgreen.svg)

> [!NOTE]
> Active personal project. Used in my own workflow. Issues triaged on a personal-time cadence.

## What it does

You define your starting cash, trading window, and condition flags in a local configuration file. The algorithm filters the available universe of equities by price, P/E ratio, revenue growth, and market cap to locate viable targets. It executes entry and exit decisions based on EMA crossovers, MACD, RSI, Stochastic, and ATR breakouts. The bot sizes positions using the Kelly criterion and manages risk by calculating dynamic stop loss targets while enforcing sector allocation caps.

## Usage

This code requires the `AlgorithmImports` module injected by the QuantConnect platform. It does not execute as a standalone script.

1. Create a project via the QuantConnect dashboard or the `lean` CLI.
2. Copy the Python files from this repository into the project root.
3. Edit `config.py` to set your backtest dates, starting cash, and parameter values.
4. Run your backtest.

To verify the isolated decision logic and price math locally:

```bash
pip install pytest
pytest
```

## License

See [LICENSE](./LICENSE).
