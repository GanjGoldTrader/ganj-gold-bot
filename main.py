import os
import json
import logging
import asyncio
import math
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ------------------------------------------------------------
# GANJ GOLD - XAUUSD analysis-only scalp engine (v1)
# M15 trend -> M5 confirmation -> M1 entry
# No automatic order execution.
# ------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    level=logging.INFO,
)

for name in ("httpx", "httpcore", "telegram", "telegram.ext", "telegram.request"):
    logging.getLogger(name).setLevel(logging.WARNING)

logger = logging.getLogger("ganj_gold")

TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN")
MARKETAPI_KEY = os.getenv("MARKETAPI_KEY")

PRICE_URL = "https://api.marketapi.app/v1/prices/latest"
BARS_URL = "https://api.marketapi.app/v1/bars"
TIMEFRAME_MINUTES = {"M1": 1, "M5": 5, "M15": 15}
LOOKBACK_HOURS = {"M1": 8, "M5": 36, "M15": 72}

# Conservative v1 guardrails. These are starting assumptions to validate,
# not proven profitable settings. Tune only after collecting paper results.
MAX_SPREAD_USD = 0.80
MAX_PRICE_AGE_SECONDS = 120
MAX_CANDLE_AGE_SECONDS = {"M1": 180, "M5": 600, "M15": 1200}
MIN_TARGET_USD = 5.0
MAX_TARGET_USD = 10.0
REWARD_RISK = 1.5
MIN_STOP_USD = MIN_TARGET_USD / REWARD_RISK
MAX_STOP_USD = MAX_TARGET_USD / REWARD_RISK


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


def parse_time(value):
    if value is None:
        raise ValueError("timestamp missing")
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def get_gold_price():
    query = urllib.parse.urlencode({"symbols": "XAUUSD"})
    result = api_get(f"{PRICE_URL}?{query}")
    data = result.get("data")
    if not isinstance(data, list) or not data:
        raise ValueError("No price data returned")

    p = data[0]
    bid = float(p["bid"])
    ask = float(p["ask"])
    if not (math.isfinite(bid) and math.isfinite(ask) and bid > 0 and ask >= bid):
        raise ValueError("Invalid bid/ask")

    return {
        "symbol": p.get("symbol", "XAUUSD"),
        "bid": bid,
        "ask": ask,
        "time": p.get("time"),
        "status": str(p.get("status", "Unknown")),
    }


def get_candles(timeframe):
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=LOOKBACK_HOURS[timeframe])
    params = urllib.parse.urlencode({
        "symbol": "XAUUSD",
        "timeframe": timeframe,
        "from": start.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "to": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "limit": 1000,
    })
    result = api_get(f"{BARS_URL}?{params}")
    data = result.get("data")
    if not isinstance(data, list):
        raise ValueError(f"Unexpected candle response: {timeframe}")

    rows = sorted(data, key=lambda item: item.get("time", ""))
    closed = []
    for candle in rows:
        if candle.get("complete") is not True:
            continue
        try:
            item = {
                "time": candle.get("time"),
                "dt": parse_time(candle.get("time")),
                "open": float(candle["open"]),
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": float(candle["close"]),
            }
            if not all(math.isfinite(item[k]) for k in ("open", "high", "low", "close")):
                continue
            if item["high"] < item["low"] or item["high"] < max(item["open"], item["close"]):
                continue
            if item["low"] > min(item["open"], item["close"]):
                continue
            closed.append(item)
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    return closed


def ema(values, period):
    if len(values) < period:
        return None
    alpha = 2.0 / (period + 1.0)
    value = sum(values[:period]) / period
    for price in values[period:]:
        value = alpha * price + (1.0 - alpha) * value
    return value


def ema_series(values, period):
    if len(values) < period:
        return []
    alpha = 2.0 / (period + 1.0)
    value = sum(values[:period]) / period
    output = [None] * (period - 1) + [value]
    for price in values[period:]:
        value = alpha * price + (1.0 - alpha) * value
        output.append(value)
    return output


def rsi(values, period=14):
    if len(values) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = ((period - 1) * avg_gain + gains[i]) / period
        avg_loss = ((period - 1) * avg_loss + losses[i]) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def atr(candles, period=14):
    if len(candles) < period + 1:
        return None
    true_ranges = []
    for i in range(1, len(candles)):
        current = candles[i]
        previous_close = candles[i - 1]["close"]
        true_ranges.append(max(
            current["high"] - current["low"],
            abs(current["high"] - previous_close),
            abs(current["low"] - previous_close),
        ))
    value = sum(true_ranges[:period]) / period
    for tr in true_ranges[period:]:
        value = ((period - 1) * value + tr) / period
    return value


def check_freshness(price, candles_by_tf):
    now = datetime.now(timezone.utc)
    if price["status"].upper() != "LIVE":
        raise ValueError(f"قیمت LIVE نیست؛ وضعیت: {price['status']}")
    price_dt = parse_time(price["time"])
    price_age = (now - price_dt).total_seconds()
    if price_age < -10 or price_age > MAX_PRICE_AGE_SECONDS:
        raise ValueError(f"قیمت قدیمی است؛ عمر داده {int(price_age)} ثانیه")

    for tf, candles in candles_by_tf.items():
        if not candles:
            raise ValueError(f"کندل {tf} موجود نیست")
        last = candles[-1]
        candle_close_time = last["dt"] + timedelta(minutes=TIMEFRAME_MINUTES[tf])
        age = (now - candle_close_time).total_seconds()
        if age < -10 or age > MAX_CANDLE_AGE_SECONDS[tf]:
            raise ValueError(f"کندل {tf} به‌روز نیست؛ عمر آخرین کندل بسته‌شده {int(age)} ثانیه")

    return price_age


def build_signal(price, candles_by_tf):
    price_age = check_freshness(price, candles_by_tf)
    spread = price["ask"] - price["bid"]
    if spread > MAX_SPREAD_USD:
        raise ValueError(f"اسپرد زیاد است: {spread:.2f} دلار")

    m1 = candles_by_tf["M1"]
    m5 = candles_by_tf["M5"]
    m15 = candles_by_tf["M15"]

    if len(m1) < 30 or len(m5) < 30 or len(m15) < 60:
        raise ValueError(
            f"تعداد کندل کافی نیست (M1={len(m1)}، M5={len(m5)}، M15={len(m15)}؛ حداقل M15=60)"
        )

    c15 = [x["close"] for x in m15]
    ema20_15 = ema(c15, 20)
    ema50_15 = ema(c15, 50)
    if ema20_15 is None or ema50_15 is None:
        raise ValueError("داده کافی برای EMA تایم‌فریم M15 نیست")

    if ema20_15 > ema50_15 and c15[-1] > ema20_15:
        trend = "BULL"
    elif ema20_15 < ema50_15 and c15[-1] < ema20_15:
        trend = "BEAR"
    else:
        trend = "NEUTRAL"

    c5 = [x["close"] for x in m5]
    ema20_5_series = ema_series(c5, 20)
    rsi5 = rsi(c5, 14)
    if len(ema20_5_series) < 2 or rsi5 is None:
        raise ValueError("داده کافی برای تحلیل M5 نیست")
    ema20_5_now = ema20_5_series[-1]
    ema20_5_prev = ema20_5_series[-2]

    if c5[-1] > ema20_5_now and ema20_5_now > ema20_5_prev and rsi5 > 52:
        confirmation = "BULL"
    elif c5[-1] < ema20_5_now and ema20_5_now < ema20_5_prev and rsi5 < 48:
        confirmation = "BEAR"
    else:
        confirmation = "NEUTRAL"

    atr1 = atr(m1, 14)
    if atr1 is None or atr1 <= 0:
        raise ValueError("ATR تایم‌فریم M1 قابل محاسبه نیست")

    last = m1[-1]
    previous = m1[-6:-1]
    if len(previous) != 5:
        raise ValueError("برای تشخیص شکست در M1 کندل کافی نیست")

    previous_high = max(x["high"] for x in previous)
    previous_low = min(x["low"] for x in previous)
    body = abs(last["close"] - last["open"])
    mid = (price["bid"] + price["ask"]) / 2.0

    direction = None
    reason = []
    if trend == "BULL" and confirmation == "BULL":
        if last["close"] > previous_high and last["close"] > last["open"] and body >= 0.25 * atr1:
            direction = "BUY"
            reason = ["روند M15 صعودی", "تأیید M5 صعودی", "شکست سقف ۵ کندل قبلی در M1"]
    elif trend == "BEAR" and confirmation == "BEAR":
        if last["close"] < previous_low and last["close"] < last["open"] and body >= 0.25 * atr1:
            direction = "SELL"
            reason = ["روند M15 نزولی", "تأیید M5 نزولی", "شکست کف ۵ کندل قبلی در M1"]

    if direction is None:
        return {
            "side": "WAIT",
            "reason": "شرایط سه تایم‌فریم برای ورود هم‌زمان کامل نیست.",
            "trend": trend,
            "confirmation": confirmation,
            "rsi5": rsi5,
            "atr1": atr1,
            "spread": spread,
            "price_age": price_age,
            "mid": mid,
        }

    if direction == "BUY":
        entry = price["ask"]
        recent_swing = min(x["low"] for x in m1[-6:])
        stop = min(recent_swing, entry - 1.2 * atr1)
        risk = entry - stop
    else:
        entry = price["bid"]
        recent_swing = max(x["high"] for x in m1[-6:])
        stop = max(recent_swing, entry + 1.2 * atr1)
        risk = stop - entry

    target_distance = risk * REWARD_RISK
    if risk < MIN_STOP_USD or risk > MAX_STOP_USD:
        return {
            "side": "WAIT",
            "reason": f"ریسک ساختاری حد ضرر ({risk:.2f}$) خارج از محدوده مناسب نسخه اول است.",
            "trend": trend,
            "confirmation": confirmation,
            "rsi5": rsi5,
            "atr1": atr1,
            "spread": spread,
            "price_age": price_age,
            "mid": mid,
        }
    if target_distance < MIN_TARGET_USD or target_distance > MAX_TARGET_USD:
        return {
            "side": "WAIT",
            "reason": f"هدف محاسباتی ({target_distance:.2f}$) خارج از بازه ۵ تا ۱۰ دلار است.",
            "trend": trend,
            "confirmation": confirmation,
            "rsi5": rsi5,
            "atr1": atr1,
            "spread": spread,
            "price_age": price_age,
            "mid": mid,
        }

    target = entry + target_distance if direction == "BUY" else entry - target_distance
    return {
        "side": direction,
        "entry": entry,
        "stop": stop,
        "target": target,
        "risk": risk,
        "target_distance": target_distance,
        "reason": "؛ ".join(reason),
        "trend": trend,
        "confirmation": confirmation,
        "rsi5": rsi5,
        "atr1": atr1,
        "spread": spread,
        "price_age": price_age,
        "mid": mid,
    }


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "سلام! به GANJ GOLD خوش آمدی. 🥇\n\n"
        "نسخه تحلیل‌گر XAUUSD فعال است؛ معامله خودکار انجام نمی‌دهد.\n\n"
        "/status - وضعیت ربات\n"
        "/price - قیمت زنده طلا\n"
        "/candles - گزارش کندل‌ها\n"
        "/signal - تحلیل BUY / SELL / WAIT\n"
        "/help - راهنما"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    await update.effective_message.reply_text(
        "🟢 GANJ GOLD فعال است.\n"
        f"زمان سرور: {now}\n"
        f"کلید MarketAPI: {'تنظیم شده' if MARKETAPI_KEY else 'تنظیم نشده'}\n"
        "موتور تحلیل: نسخه آزمایشی v1"
    )


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.effective_message.reply_text("در حال دریافت قیمت زنده XAUUSD...")
        p = await asyncio.to_thread(get_gold_price)
        await update.effective_message.reply_text(
            "🥇 GANJ GOLD | قیمت طلا\n\n"
            f"نماد: {p['symbol']}\n"
            f"Bid: {p['bid']:.2f}\n"
            f"Ask: {p['ask']:.2f}\n"
            f"Spread: {p['ask'] - p['bid']:.2f}\n"
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
        "در حال دریافت کندل‌های XAUUSD...\nلطفاً کمی صبر کن."
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
            if rows:
                for c in rows[-3:]:
                    lines.append(
                        f"\nزمان: {c['time']}\n"
                        f"O: {c['open']:.2f} | H: {c['high']:.2f}\n"
                        f"L: {c['low']:.2f} | C: {c['close']:.2f}"
                    )
            else:
                lines.append("⚠️ کندل بسته‌شده‌ای دریافت نشد.")
            lines.append("")
        lines.append("ℹ️ فقط کندل‌های complete=true نمایش داده شده‌اند.")
        await message.edit_text("\n".join(lines))
    except Exception as error:
        logger.exception("CANDLES failed")
        await message.edit_text(
            "❌ دریافت کندل ناموفق بود.\n"
            f"نوع خطا: {type(error).__name__}"
        )


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = await update.effective_message.reply_text(
        "🧠 در حال تحلیل M15، M5 و M1...\n"
        "چهار درخواست داده به MarketAPI ارسال می‌شود."
    )
    try:
        price_task = asyncio.to_thread(get_gold_price)
        candle_tasks = {
            tf: asyncio.to_thread(get_candles, tf)
            for tf in ("M1", "M5", "M15")
        }
        p = await price_task
        candle_results = {}
        for tf, task in candle_tasks.items():
            candle_results[tf] = await task

        result = build_signal(p, candle_results)
        if result["side"] == "WAIT":
            text = (
                "⏸ GANJ GOLD | WAIT\n\n"
                f"دلیل: {result['reason']}\n\n"
                f"روند M15: {result['trend']}\n"
                f"تأیید M5: {result['confirmation']}\n"
                f"RSI M5: {result['rsi5']:.1f}\n"
                f"ATR M1: {result['atr1']:.2f}$\n"
                f"Spread: {result['spread']:.2f}$\n"
                f"قیمت میانی: {result['mid']:.2f}\n"
                f"تازگی قیمت: {result['price_age']:.0f} ثانیه\n\n"
                "این نسخه آزمایشی است؛ WAIT یعنی شرایط ورود کامل نیست."
            )
        else:
            text = (
                f"🥇 GANJ GOLD | {result['side']}\n\n"
                f"ورود مرجع: {result['entry']:.2f}\n"
                f"حد ضرر: {result['stop']:.2f}\n"
                f"حد سود: {result['target']:.2f}\n"
                f"ریسک: {result['risk']:.2f}$\n"
                f"هدف: {result['target_distance']:.2f}$\n"
                f"نسبت سود به ضرر: 1:{REWARD_RISK:.1f}\n\n"
                f"دلیل: {result['reason']}\n"
                f"RSI M5: {result['rsi5']:.1f}\n"
                f"ATR M1: {result['atr1']:.2f}$\n"
                f"Spread: {result['spread']:.2f}$\n"
                f"اعتبار پیشنهادی: حداکثر ۵ دقیقه یا تا بسته‌شدن کندل بعدی M1\n\n"
                "⚠️ سیگنال آزمایشی است؛ قبل از معامله واقعی باید در حساب دمو ارزیابی شود."
            )
        await message.edit_text(text)
    except Exception as error:
        logger.exception("SIGNAL failed")
        await message.edit_text(
            "⏸ GANJ GOLD | WAIT\n\n"
            f"تحلیل ایمن متوقف شد: {type(error).__name__}\n"
            f"جزئیات: {str(error)[:250]}\n\n"
            "تا رفع مشکل داده یا اتصال، سیگنال خرید و فروش صادر نمی‌شود."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "GANJ GOLD | راهنما\n\n"
        "/start - شروع\n"
        "/status - وضعیت اتصال\n"
        "/price - قیمت زنده XAUUSD\n"
        "/candles - گزارش کندل‌ها\n"
        "/signal - تحلیل آزمایشی BUY / SELL / WAIT\n"
        "/help - راهنما\n\n"
        "تحلیل بر اساس M15، M5 و M1 انجام می‌شود.\n"
        "ربات فعلاً هیچ معامله‌ای را خودکار اجرا نمی‌کند."
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
