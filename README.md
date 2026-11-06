# GANJ GOLD

Telegram-based XAUUSD analysis bot. It produces analysis-only BUY / SELL / WAIT messages and does **not** execute trades.

## Runtime configuration

Set these environment variables in the deployment service:

- `TELEGRAM_TOKEN` (or `BOT_TOKEN`): Telegram bot token.
- `MARKETAPI_KEY`: MarketAPI key with both `read:latest` and `read:ohlcv` scopes.

Never commit API keys or Telegram tokens to this repository, and do not send them in chat.

## Telegram commands

- `/start` — welcome and command list
- `/status` — checks the MarketAPI XAUUSD quote, LIVE status, and data age
- `/price` — latest XAUUSD Bid / Ask
- `/candles` — latest closed M1, M5, and M15 candles
- `/signal` — experimental M15 trend + M5 confirmation + M1 entry analysis
- `/help` — command reference

A successful `/status` check is cached for 30 seconds to avoid unnecessary price requests.

## Local development

```bash
python -m pip install -r requirements.txt
python -m compileall -q .
python -m unittest discover -s tests -v
python main.py
```

## Safety and validation

- Signal rules are experimental and are not evidence of profitability.
- Validate signals with historical testing and a demo account before considering live use.
- The bot does not place, modify, or close orders.
- GitHub Actions runs Python compilation and unit tests on changes to the development branch and pull requests to `main`.
