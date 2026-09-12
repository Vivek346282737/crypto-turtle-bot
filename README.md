# Crypto Turtle Bot

A modular, production-oriented algorithmic cryptocurrency trading system built with clean architectural principles, rigorous risk management, and multi-exchange support via CCXT.

## Disclaimer
This is research and engineering software. No profitability guarantees, fixed returns, or 100% accuracy claims are made. Use at your own risk.

## Architecture
`mermaid
graph TD
    A[Market Data] --> B[Feature Engineering];
    B --> C[Regime Detection]
    C --> D[Strategy Engine]
    D --> E[Signal Validation]
    E --> F[Risk Engine]
    F --> G[Position Sizing]
    H --> I[Execution Engine]
    I --> J[Portfolio / Position Management]
    J --> K[Monitoring / Audit]
`

## Overview & Features
- **Exchange Abstraction:** Unified CCXT integration supporting Binance, Bybit, OKX, and others.
- **Risk Management:** Absolute capital protection, stop-losses, and daily drawdown kill-switches.
- **Regime Detection:** Automated tracking of market states (Trend Up, Trend Down, Range).
- **Backtesting Engine:** Realistic execution simulation incorporating fees and slippage.
- **Robust Testing:** Full pytest unit test suite and GitHub Actions CI/CD pipeline.

## Quick Start
`powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -e .
copy .env.example .env
pytest
python scripts/run_bot.py
`
