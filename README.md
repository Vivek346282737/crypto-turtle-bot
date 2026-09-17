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
- **Trend & Volatility Filters:** 200 EMA macro-trend alignment and ADX-based chop suppression ($ADX \ge 22$) to filter false breakouts during low-volatility ranges.
- **Chandelier ATR Dynamic Trailing:** Ratchet stop-loss mechanisms driven by $2.5 \times ATR$ offsets trailing from highest/lowest trade marks to protect unrealized profits.
- **Turtle Pyramiding Logic:** Automated multi-unit position scaling up to 3 units on favorable $0.5 \times ATR$ trends with baseline break-even risk adjustment.
- **Funding Rate Guardrails:** Real-time derivative drag protection halting trades during extreme positive or negative funding environments.
- **Circuit Breaker Automation:** Automated 24-hour trade pause upon encountering 3 consecutive stop-losses to mitigate adverse market regimes.
- **Persistent State Storage:** ACID-compliant SQLite local database tracking active positions, execution states, and historical trade audits across container restarts.
- **God-Level HTML Email Alerts:** Real-time, styled responsive email reporting covering trade fills, entry/exit metrics, duration, net PnL, and ROI.
- **Dockerized Cloud Deployment:** Fully containerized architecture running 24/7 on AWS EC2 with automatic volume mounts and restart policies.

## Architecture
```mermaid
graph TD
    A[Market Data] --> B[Feature Engineering]
    B --> C[Regime Detection]
    C --> D[Strategy Engine]
    D --> E[Signal Validation: EMA200 / ADX / Volume]
    E --> F[Risk Engine: Funding & Circuit Breaker]
    F --> G[Position Sizing & Pyramiding]
    G --> H[Execution Engine]
    H --> I[SQLite Persistence & Chandelier ATR Ratchet]
    I --> J[Monitoring / SMTP HTML Audit Dispatch]