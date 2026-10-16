# Portfolio Dashboard

A self-hosted dashboard for tracking an investment portfolio spread across several bank accounts. It consolidates positions and returns, compares them with benchmarks, and sends a daily report by email.

## Features

- Consolidated positions across banks, with prices and FX updated automatically (Yahoo Finance)
- Returns: previous day, intraday, month to date, year to date and since purchase
- Monthly returns by bank and for the weighted portfolio, with charts and benchmark comparison (S&P 500, T-Bills)
- Allocation by asset class and by sector, plus the top 10 positions
- Cash and dividends page
- Intraday move alerts by email
- Daily email report, with an optional AI-written bulletin (Anthropic API) built from market data and free news headlines
- Daily database backup to Google Cloud Storage
- CSV exports
- Login per user, with sessions that expire after 5 minutes of inactivity
- Light and dark themes

## Stack

Python, Flask, MySQL, APScheduler, yfinance, matplotlib, Chart.js, Gunicorn and Nginx.

## Running it

1. Create a MySQL database and copy `.env.example` to `.env`, filling in your values.
2. Install the dependencies: `pip install -r requirements.txt`.
3. Create a dashboard user: `python create_user.py <username>`.
4. Start the dashboard with `python run_dashboard.py`, and the scheduler with `python scheduler_worker.py`.

The `deploy/` folder has example systemd services and an Nginx site configuration for a Linux server.

## Notes

- No portfolio data or statements are included. You need to load your own positions and monthly history.
- Secrets are never stored in the code: everything is read from the `.env` file.
