import io
import unittest
import urllib.error
from unittest.mock import patch

import main


class ParseTimeTests(unittest.TestCase):
    def test_parses_iso_utc_timestamp(self):
        parsed = main.parse_time("2026-11-05T19:43:00Z")
        self.assertEqual(parsed.isoformat(), "2026-11-05T19:43:00+00:00")

    def test_parses_unix_seconds(self):
        parsed = main.parse_time(1793907780)
        self.assertEqual(parsed.tzinfo, main.timezone.utc)

    def test_rejects_missing_timestamp(self):
        with self.assertRaises(ValueError):
            main.parse_time(None)


class IndicatorTests(unittest.TestCase):
    def test_ema_uses_seed_average_and_smoothing(self):
        self.assertAlmostEqual(main.ema([1, 2, 3, 4], 3), 3.0)

    def test_rsi_is_100_for_only_gains(self):
        self.assertEqual(main.rsi(list(range(1, 17)), 14), 100.0)

    def test_atr_returns_none_when_history_is_too_short(self):
        self.assertIsNone(main.atr([], 14))



class MarketApiPayloadTests(unittest.TestCase):
    def test_latest_price_accepts_documented_decimal_string_fields(self):
        payload = {
            "data": [{
                "symbol": "XAUUSD",
                "bid": "4000.10",
                "ask": "4000.35",
                "time": "2026-11-05T19:43:00.000Z",
                "status": "LIVE",
            }]
        }
        with patch.object(main, "api_get", return_value=payload):
            price = main.get_gold_price()

        self.assertEqual(price["symbol"], "XAUUSD")
        self.assertAlmostEqual(price["bid"], 4000.10)
        self.assertAlmostEqual(price["ask"], 4000.35)
        self.assertEqual(price["status"], "LIVE")
        self.assertIsNotNone(main.parse_time(price["time"]))

    def test_bars_accepts_documented_ohlc_payload(self):
        payload = {
            "data": [{
                "time": "2026-11-05T19:43:00Z",
                "open": "4000.00",
                "high": "4002.00",
                "low": "3999.50",
                "close": "4001.25",
                "complete": True,
            }]
        }
        with patch.object(main, "api_get", return_value=payload):
            candles = main.get_candles("M1")

        self.assertEqual(len(candles), 1)
        self.assertEqual(candles[0]["close"], 4001.25)
        self.assertEqual(candles[0]["time"], "2026-11-05T19:43:00Z")


class MarketApiErrorTests(unittest.TestCase):
    def test_missing_key_fails_before_network_request(self):
        with patch.object(main, "MARKETAPI_KEY", ""):
            with self.assertRaisesRegex(main.MarketAPIError, "MARKETAPI_KEY"):
                main.api_get("https://example.invalid")

    def test_http_error_preserves_status_and_api_code(self):
        body = io.BytesIO(
            b'{"code":"invalid_api_key","detail":"API key rejected","request_id":"req-test"}'
        )
        error = urllib.error.HTTPError(
            "https://api.marketapi.app/test",
            401,
            "Unauthorized",
            {},
            body,
        )
        with patch.object(main.urllib.request, "urlopen", side_effect=error):
            with patch.object(main, "MARKETAPI_KEY", "test-secret"):
                with self.assertRaises(main.MarketAPIError) as caught:
                    main.api_get("https://api.marketapi.app/test")

        self.assertEqual(caught.exception.status_code, 401)
        self.assertEqual(caught.exception.error_code, "invalid_api_key")
        self.assertIn("req-test", str(caught.exception))
        self.assertNotIn("test-secret", str(caught.exception))

    def test_network_error_is_reported_as_market_api_error(self):
        with patch.object(main, "MARKETAPI_KEY", "test-secret"):
            with patch.object(
                main.urllib.request,
                "urlopen",
                side_effect=urllib.error.URLError("connection refused"),
            ):
                with self.assertRaises(main.MarketAPIError) as caught:
                    main.api_get("https://api.marketapi.app/test")

        self.assertIn("ارتباط", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
