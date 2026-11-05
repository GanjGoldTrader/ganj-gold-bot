
import os
import json
import logging
import asyncio
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    level=logging.INFO,
)

for name in ("httpx", "httpcore", "telegram",
             "telegram.ext", "telegram.request"):
    logging.getLogger(name).setLevel(logging.WARNING)

logger = logging.getLogger("ganj_gold")

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
MARKETAPI_KEY = os.getenv("MARKETAPI_KEY")

PRICE_URL = "https://api.marketapi.app/v1/prices/latest"
BARS_URL = "https://api.marketapi.app/v1/bars"


def api_get(url):
    if not MARKETAPI_KEY:
        raise RuntimeError("MARKETAPI_KEY is missing")

    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {MARKETAPI_KEY}",
            "Accept": "application/json",
        },
        method="GET",
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def get_gold_price():
    query = urllib.parse.urlencode({"symbols": "XAUUSD"})
    result = api_get(f"{PRICE_URL}?{query}")

    data = result.get("data")
    if not isinstance(data, list) or not data:
        raise ValueError("No price data returned")

    p = data[0]
    return {
        "symbol": p.get("symbol", "XAUUSD"),
        "bid": p.get("bid"),
        "ask": p.get("ask"),
        "time": p.get("time", "Unknown"),
        "status": p.get("status", "Unknown"),
    }


def get_candles(timeframe):
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=8)

    params = urllib.parse.urlencode({
        "symbol": "XAUUSD",
        "timeframe": timeframe,
        "from": start.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "to": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "limit": 50,
    })

    result = api_get(f"{BARS_URL}?{params}")
    data = result.get("data")

    if not isinstance(data, list):
        raise ValueError(f"Unexpected candle response: {timeframe}")

    candles = sorted(
        data,
        key=lambda item: item.get("time", "")
    )

    closed = [
        c for c in candles
        if c.get("complete") is True
    ]

    return closed


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "سلام! به GANJ GOLD خوش آمدی. 🥇\n\n"
        "ربات فعال است.\n\n"
        "/status - وضعیت ربات\n"
        "/price - قیمت زنده طلا\n"
        "/candles - دریافت کندل‌های M1، M5 و M15\n"
        "/signal - وضعیت سیگنال\n"
        "/help - راهنما"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    await update.effective_message.reply_text(
        "🟢 GANJ GOLD فعال است.\n"
        f"زمان سرور: {now}\n"
        f"کلید MarketAPI: {'تنظیم شده' if MARKETAPI_KEY else 'تنظیم نشده'}"
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.effective_message.reply_text(
            "در حال دریافت قیمت زنده XAUUSD..."
        )

        p = await asyncio.to_thread(get_gold_price)

        await update.effective_message.reply_text(
            "🥇 GANJ GOLD | قیمت طلا\n\n"
            f"نماد: {p['symbol']}\n"
            f"Bid: {p['bid']}\n"
            f"Ask: {p['ask']}\n"
            f"وضعیت داده: {p['status']}\n"
            f"زمان داده: {p['time']}"
        )

    except Exception as error:
        logger.exception("PRICE failed")
        await update.effective_message.reply_text(
            f"❌ خطا در دریافت قیمت: {type(error).__name__}"
        )


async def candles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = await update.effective_message.reply_text(
        "در حال دریافت کندل‌های XAUUSD...\n"
        "لطفاً کمی صبر کن."
    )

    try:
        results = {}

        for tf in ("M1", "M5", "M15"):
            results[tf] = await asyncio.to_thread(get_candles, tf)

        lines = ["🥇 GANJ GOLD | گزارش کندل‌ها", ""]

        for tf in ("M1", "M5", "M15"):
            rows = results[tf]

            lines.append(f"📊 تایم‌فریم {tf}")
            lines.append(f"تعداد کندل بسته‌شده: {len(rows)}")

            if not rows:
                lines.append("⚠️ کندل بسته‌شده‌ای دریافت نشد.")
                lines.append("")
                continue

            for c in rows[-3:]:
                lines.append(
                    f"\nزمان: {c.get('time', '?')}\n"
                    f"O: {c.get('open', '?')} | "
                    f"H: {c.get('high', '?')}\n"
                    f"L: {c.get('low', '?')} | "
                    f"C: {c.get('close', '?')}"
                )

            lines.append("")

        lines.append(
            "ℹ️ فقط کندل‌های complete=true نمایش داده شده‌اند.\n"
            "این گزارش هنوز سیگنال معاملاتی نیست."
        )

        await message.edit_text("\n".join(lines))

    except Exception as error:
        logger.exception("CANDLES failed")
        await message.edit_text(
            "❌ دریافت کندل ناموفق بود.\n"
            f"نوع خطا: {type(error).__name__}\n"
            "لطفاً لاگ سرور را بررسی کنیم."
        )


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "⏸ فعلاً WAIT\n\n"
        "تحلیل M1، M5 و M15 هنوز فعال نشده است."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "GANJ GOLD | راهنما\n\n"
        "/start - شروع\n"
        "/status - وضعیت اتصال\n"
        "/price - قیمت زنده XAUUSD\n"
        "/candles - دریافت کندل‌ها\n"
        "/signal - وضعیت سیگنال\n"
        "/help - راهنما"
    )


async def error_handler(update, context):
    error = context.error
    logger.error(
        "Unhandled handler error: %s",
        type(error).__name__ if error else "Unknown",
        exc_info=error,
    )


def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN is missing")

    logger.info(
        "GANJ GOLD starting; MarketAPI key configured=%s",
        bool(MARKETAPI_KEY),
    )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("candles", candles))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("help", help_command))

    app.add_error_handler(error_handler)

    logger.info("Telegram handlers registered")
    app.run_polling()


if __name__ == "__main__":
    main()
