# Crypto Turtle Bot

A modular, production-oriented algorithmic cryptocurrency trading system with systematic strategies, regime detection, risk management, backtesting, and automated execution.

## Disclaimer
This is research and engineering software. No guaranteed profitability, fixed returns, or absolute capital protection claims are made. Use at your own risk.

## Overview
Crypto Turtle Bot is a systematic quantitative trading framework engineered for reliable execution across CCXT-compatible cryptocurrency exchanges. It separates market data ingestion, feature engineering, regime detection, risk evaluation, and idempotent order execution into discrete, testable modules.

## Features
- **Exchange Abstraction:** Unified CCXT integration supporting Binance, Bybit, OKX, and other exchanges.
- **Rigorous Risk Management:** Position sizing, stop-loss calculations, daily drawdown limits, and emergency kill-switches.
- **Regime Detection:** Automated classification of market states (Trend Up, Trend Down, Range).
- **Backtesting Engine:** Realistic performance simulation incorporating fees and slippage.
- **Automated CI/CD & Testing:** Full pytest unit test suite and GitHub Actions workflow.

## Architecture
`mermaid
graph TD
    A[Market Data] --> B[Feature Engineering]
    B --> C[Regime Detection]
    C --> D[Strategy Engine]
    D --> E[Signal Validation]
    E --> F[Risk Engine]
    F --> G[Position Sizing]
    G --> H[Execution Engine]
    H --> I[Portfolio / Position Management]
    I --> J[Monitoring / Audit]
``n
## Quick Start
`powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -e .
copy .env.example .env
pytest
python scripts/run_bot.py
`
