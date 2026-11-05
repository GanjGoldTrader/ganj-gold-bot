
import os
import json
import logging
import asyncio
import urllib.request
import urllib.parse
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    level=logging.INFO,
)

# Hide request details and prevent credentials from appearing in routine logs
for logger_name in (
    "httpx",
    "httpcore",
    "telegram",
    "telegram.ext",
    "telegram.request",
):
    logging.getLogger(logger_name).setLevel(logging.WARNING)

logger = logging.getLogger("ganj_gold")

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
            raise ValueError("MarketAPI returned an empty data list")
        price_data = data[0]
    elif isinstance(data, dict):
        price_data = data
    else:
        raise ValueError("Unexpected MarketAPI response format")

    return {
        "symbol": price_data.get("symbol", "XAUUSD"),
        "bid": price_data.get("bid"),
        "ask": price_data.get("ask"),
        "time": price_data.get("time", "Unknown"),
        "status": price_data.get("status", "Unknown"),
    }


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("START command received")

    await update.effective_message.reply_text(
        "سلام! به GANJ GOLD خوش آمدی. 🥇\n\n"
        "ربات فعال است.\n\n"
        "دستورات:\n"
        "/status - وضعیت ربات\n"
        "/price - قیمت زنده طلا\n"
        "/signal - وضعیت سیگنال\n"
        "/help - راهنما"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("STATUS command received")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    await update.effective_message.reply_text(
        "🟢 GANJ GOLD فعال است.\n"
        f"زمان سرور: {now}\n"
        f"کلید MarketAPI: {'تنظیم شده' if MARKETAPI_KEY else 'تنظیم نشده'}"
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("PRICE command received")

    try:
        await update.effective_message.reply_text(
            "در حال دریافت قیمت زنده XAUUSD..."
        )
        logger.info("PRICE acknowledgement sent; requesting MarketAPI")

        p = await asyncio.to_thread(get_gold_price)

        logger.info(
            "MarketAPI response received; status=%s",
            p["status"],
        )

        await update.effective_message.reply_text(
            "🥇 GANJ GOLD | قیمت طلا\n\n"
            f"نماد: {p['symbol']}\n"
            f"Bid: {p['bid']}\n"
            f"Ask: {p['ask']}\n"
            f"وضعیت داده: {p['status']}\n"
            f"زمان داده: {p['time']}\n\n"
            "این مرحله فقط آزمایش دریافت قیمت است."
        )

        logger.info("PRICE response sent to Telegram")

    except Exception as error:
        logger.exception(
            "PRICE command failed; error_type=%s",
            type(error).__name__,
        )

        try:
            await update.effective_message.reply_text(
                "❌ دریافت قیمت ناموفق بود.\n"
                f"نوع خطا: {type(error).__name__}\n"
                "لطفاً لاگ سرور را بررسی کنیم."
            )
        except Exception:
            logger.exception("Could not send PRICE error message")


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("SIGNAL command received")

    await update.effective_message.reply_text(
        "⏸ فعلاً WAIT\n\n"
        "دریافت و اعتبارسنجی قیمت باید تکمیل شود.\n"
        "هنوز تحلیل کندل‌های M1، M5 و M15 فعال نیست."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("HELP command received")

    await update.effective_message.reply_text(
        "GANJ GOLD | راهنما\n\n"
        "/start - شروع\n"
        "/status - وضعیت اتصال\n"
        "/price - قیمت زنده XAUUSD\n"
        "/signal - وضعیت سیگنال\n"
        "/help - راهنما"
    )


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    error = context.error

    logger.error(
        "Unhandled Telegram handler error; error_type=%s",
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
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("help", help_command))

    app.add_error_handler(error_handler)

    logger.info("Telegram command handlers registered")
    app.run_polling()


if __name__ == "__main__":
    main()
