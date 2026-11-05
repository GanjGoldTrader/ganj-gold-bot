import os
import logging
from datetime import datetime, timezone

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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! به GANJ GOLD خوش آمدی. 🥇\n\n"
        "ربات با موفقیت فعال شده است.\n\n"
        "دستورات:\n"
        "/status - وضعیت ربات\n"
        "/signal - بررسی وضعیت سیگنال\n"
        "/help - راهنما"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    await update.message.reply_text(
        "🟢 GANJ GOLD فعال است.\n"
        f"زمان سرور: {now}\n"
        "وضعیت دریافت قیمت: هنوز متصل نشده"
    )


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⏸ فعلاً WAIT\n\n"
        "خوراک قیمت زنده هنوز متصل نشده است.\n"
        "تا زمان تأیید داده‌های معتبر، سیگنال خرید یا فروش صادر نمی‌شود."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "GANJ GOLD | راهنمای ربات\n\n"
        "/start - شروع\n"
        "/status - وضعیت اتصال\n"
        "/signal - وضعیت سیگنال\n"
        "/help - راهنما\n\n"
        "استراتژی موردنظر: M15 جهت، M5 تأیید، M1 ورود."
    )


def main():
    if not TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN is missing!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("help", help_command))

    logging.info("GANJ GOLD bot is starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
