import os
import json
import logging
import asyncio
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
MARKETAPI_KEY = os.getenv("MARKETAPI_KEY")

API_URL = "https://api.marketapi.app/v1/prices/latest"


def get_gold_price():
    if not MARKETAPI_KEY:
        raise RuntimeError("MARKETAPI_KEY is missing")

    query = urllib.parse.urlencode({"symbols": "XAUUSD"})
    request = urllib.request.Request(
        f"{API_URL}?{query}",
        headers={
            "Authorization": f"Bearer {MARKETAPI_KEY}",
            "Accept": "application/json",
        },
        method="GET",
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        result = json.loads(response.read().decode("utf-8"))

    data = result.get("data")

    if isinstance(data, list):
        if not data:
            raise ValueError("No price data returned")
        price = data[0]
    elif isinstance(data, dict):
        price = data
    else:
        raise ValueError("Unexpected API response")

    return {
        "symbol": price.get("symbol", "XAUUSD"),
        "bid": price.get("bid"),
        "ask": price.get("ask"),
        "time": price.get("time", "Unknown"),
        "status": price.get("status", "Unknown"),
    }


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! به GANJ GOLD خوش آمدی. 🥇\n\n"
        "ربات فعال است.\n\n"
        "دستورات:\n"
        "/status - وضعیت ربات\n"
        "/price - قیمت زنده طلا\n"
        "/signal - وضعیت سیگنال\n"
        "/help - راهنما"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    await update.message.reply_text(
        "🟢 GANJ GOLD فعال است.\n"
        f"زمان سرور: {now}\n"
        f"کلید MarketAPI: {'تنظیم شده' if MARKETAPI_KEY else 'تنظیم نشده'}"
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("در حال دریافت قیمت زنده XAUUSD...")

    try:
        p = await asyncio.to_thread(get_gold_price)

        await update.message.reply_text(
            "🥇 GANJ GOLD | قیمت طلا\n\n"
            f"نماد: {p['symbol']}\n"
            f"Bid: {p['bid']}\n"
            f"Ask: {p['ask']}\n"
            f"وضعیت داده: {p['status']}\n"
            f"زمان داده: {p['time']}\n\n"
            "این مرحله فقط آزمایش دریافت قیمت است."
        )

    except Exception as e:
        logging.error("MarketAPI price request failed: %s", type(e).__name__)
        await update.message.reply_text(
            "❌ دریافت قیمت ناموفق بود.\n"
            "اتصال یا تنظیمات API را باید بررسی کنیم."
        )


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⏸ فعلاً WAIT\n\n"
        "دریافت و اعتبارسنجی قیمت باید تکمیل شود.\n"
        "هنوز تحلیل کندل‌های M1، M5 و M15 فعال نیست."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "GANJ GOLD | راهنما\n\n"
        "/start - شروع\n"
        "/status - وضعیت ربات\n"
        "/price - قیمت زنده XAUUSD\n"
        "/signal - وضعیت سیگنال\n"
        "/help - راهنما"
    )


def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN is missing")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("help", help_command))

    logging.info("GANJ GOLD bot is starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
