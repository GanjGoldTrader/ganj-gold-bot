# GANJ GOLD — Master Specification & Project Archive

> Durable source of truth for decisions, requirements, roadmap, implementation status, and handover between conversations. Update after every substantial project conversation. Never store API keys, bot tokens, passwords, or other secrets here.

**Last updated:** 2026-11-06  
**Repository:** `GanjGoldTrader/ganj-gold-bot`  
**Development PR:** [#1 — MarketAPI diagnostics and live health check](https://github.com/GanjGoldTrader/ganj-gold-bot/pull/1)

## 1. Archive maintenance rules
- At the end of every substantial GANJ GOLD conversation, identify new requirements, decisions, corrections, discoveries, code changes, test results, and open questions.
- Update the relevant sections and append a dated entry to Project archive / decision log.
- Label each item Confirmed, Proposed, In progress, or Pending validation. Never present a proposal as an agreed implementation.
- Commit documentation changes to the active development branch and include them in the appropriate PR. Do not merge or deploy without the release gates below.
- At the start of a new project conversation, read this file and inspect current GitHub/PR/CI state. Current repository state supersedes old chat summaries.

## 2. Objective and principles
Build a reliable XAUUSD short-term analysis assistant combining technical analysis, market-data quality checks, fundamental/news context, and clear Telegram alerts. Accuracy and capital preservation outrank signal frequency. Explain evidence and invalidation. Separate facts, reported claims, interpretation, and forecasts. Do not claim profitability without robust out-of-sample evidence.
**Scope:** analysis and alerts only. No automatic order placement, modification, or closing.

## 3. Confirmed strategy baseline
| Item | Baseline |
|---|---|
| Instrument | XAUUSD |
| Horizon | Generally 5–30 minutes |
| Planning move | About $5–$10; not guaranteed or a fixed TP rule |
| M15 | Main directional context / trend filter |
| M5 | Setup confirmation |
| M1 | Entry timing / trigger |
| Outputs | BUY, SELL, WAIT plus operational states |
| Visual reference | TradingView OANDA:XAUUSD |
| Execution | Alerts only; no automatic trades |

Risk/reward, volatility, spread, and regime must determine whether a setup is valid; the $5–$10 range is only a planning reference.

## 4. Signal colors and message contract
**Proposed palette — pending implementation and Telegram rendering tests:**
| Color | Label | Meaning |
|---|---|---|
| Green | BUY / خرید | Valid long setup after all filters pass |
| Red | SELL / فروش | Valid short setup after all filters pass |
| Yellow/amber | WAIT / صبر | No valid entry, incomplete confirmation, or conflicting evidence |
| Gray | MARKET CLOSED / NO DATA | Closed session, stale quote, missing data, or quality failure |
| Blue | NEWS ALERT / هشدار خبری | Material scheduled or unscheduled event |

Always show a literal text label; color alone is insufficient. A signal should show direction, calibrated confidence tier (only after validation), M15/M5/M1 reasoning, entry reference, stop-loss, take-profit, risk/reward, validity window, spread, quote timestamp, supporting/contradicting evidence, and invalidation conditions. Do not invent probability or price levels.

**Safety gates:** force WAIT or an operational warning if the provider reports closed, quotes are stale/malformed/crossed, candle history is missing/incomplete/misaligned, spread or volatility exceeds tested limits, or configured event-risk rules block trading. API failure is not the same as market closure.

## 5. Market calendar and time handling
- Store and compare timestamps in UTC; use timezone-aware datetimes everywhere.
- Display local times with an explicit timezone. Use IANA zones so daylight-saving changes are handled automatically.
- Use the actual configured provider/broker's official XAUUSD schedule as the operational authority. Providers do not necessarily share identical hours.
- Handle weekly closure, daily maintenance breaks, holidays, special sessions, and DST.
- Reconcile schedule with provider status/quote freshness. A schedule alone cannot prove a quote is live.
- Show next scheduled reopening only when the provider calendar supports a reliable calculation; otherwise state that it is subject to provider confirmation.

**Example only:** OANDA's published XAU/USD schedule has commonly been listed as Sunday 18:05 through Friday 16:59 New York time, with a daily maintenance interval around 17:00–18:05 New York time. This is not universal. Verify current official hours and the actual MarketAPI underlying source before implementing. Holidays and DST may change local-clock equivalents.

**Closed message (FA):** بازار XAUUSD در منبع قیمت فعلی بسته است. بازگشایی برنامه‌ریزی‌شده: [تاریخ، ساعت و منطقه زمانی]. تا دریافت قیمت معتبر، سیگنال خرید یا فروش صادر نمی‌شود.

**Closed message (EN):** XAUUSD is closed according to the configured provider. Scheduled reopening: [date, time, timezone]. No BUY/SELL signal will be issued until valid market data is available.

Use a distinct DATA STALE / DATA UNAVAILABLE message for API/data problems. Do not report market closed merely because an API request failed.

## 6. Fundamental analysis and news intelligence
Build a separate news/fundamental subsystem. It must collect, timestamp, deduplicate, corroborate, classify, and interpret material events, then pass structured context to the decision engine. Headlines alone must never directly trigger BUY/SELL.

### Candidate source groups (not all connected yet)
- US official macro/policy: Federal Reserve/FOMC; BLS (CPI, PPI, labor); BEA (PCE, GDP, income/spending); US Treasury; Census Bureau; ISM (clearly label as an industry association).
- Gold/commodities/positioning: World Gold Council, LBMA, CME/COMEX notices and data, CFTC COT (publication lag must be disclosed), EIA when energy context matters.
- International reporting and geopolitics: Reuters, Associated Press, Bloomberg and other reputable newsrooms; relevant government and international-organization primary statements.
- Iran: relevant official economic/monetary/energy/government releases, reputable Iranian news agencies, and independent reporting. Compare material claims across sources.
- Prefer primary sources, documented APIs, RSS, or licensed feeds. Respect terms, rate limits, and copyright. These are candidate sources, not a claim of existing API access.

### News verification record
For each material event retain canonical event ID/topic; original publication time and timezone; ingestion/update times; source and URL; primary/secondary classification; concise paraphrase; corroborating sources; contradictions, denials, corrections; status (unverified, single-source, corroborated, officially confirmed, disputed, corrected); category; affected assets; relevance; expiry/decay; and observed market reaction separately from predicted impact.

Do not treat syndicated copies of one wire story as independent corroboration. Preserve original publication time when an article is updated. Clearly label anonymous-source reporting, commentary, rumors, and unverified claims.

### Economic calendar
Track CPI/Core CPI, PPI/Core PPI, PCE/Core PCE, NFP, unemployment, hourly earnings, JOLTS, ADP (separate private estimate), FOMC decisions/minutes/press conferences/speeches, GDP, retail sales, ISM, jobless claims, relevant non-US central-bank decisions, and major geopolitical/trade/sanctions events.

For each release store scheduled time/timezone, previous, consensus, actual, revisions, source, release status, and retrieval timestamp. Never invent missing consensus. Keep revisions distinct from the first release.

### Fundamental interpretation and integration
Assess USD, nominal/real yields, rate expectations, inflation/growth/labor surprises, safe-haven demand, central-bank gold demand, ETF flows, futures positioning (with data lag), energy, and geopolitics. Avoid simplistic rules such as 'higher CPI always means gold falls'; consider expectations and observed reaction. Use configurable, tested event-risk windows. A news alert is not a trade signal. Technical and fundamental outputs remain separately visible; material event risk or contradictory verified information may downgrade a setup to WAIT.

## 7. Language and Telegram UX
Required modes: Persian, English, and bilingual (Persian first, English second). Recommended initial default: Persian, with a user-selectable preference. Keep localization separate from calculations and signal logic. Translate commands, errors, status, market-hours messages, news alerts, and signals consistently.

Message fields when available: status; market state; M15 trend; M5 confirmation; M1 trigger; entry; stop-loss; take-profit; validity; spread; data timestamp; rationale; invalidation. If a valid entry is absent, show WAIT and do not invent levels.

## 8. Target architecture
1. Market-data adapter (auth, quote/OHLCV, normalization, timestamps, retries, limits).
2. Provider session calendar (weekly/daily hours, holidays, DST, next open).
3. Data-quality/health layer (freshness, completeness, continuity, spread, provider status).
4. Technical engine (indicators and multi-timeframe setup).
5. News ingestion (primary feeds, RSS/API, source metadata, deduplication).
6. Economic calendar (scheduled/actual/forecast/previous values).
7. Verification/corroboration (independence, contradictions, corrections).
8. Fundamental context engine.
9. Decision/risk layer (technical + fundamental + event risk + data quality; may return WAIT).
10. Localization/presentation (FA, EN, bilingual; labels/colors).
11. Telegram interface and preferences.
12. Audit, replay, backtesting, and metrics.

### System flowchart
```mermaid
flowchart TD
 A[Market Data Providers] --> B[Data Adapter]
 C[Provider Session Calendar] --> D[Market Status and Next Open]
 B --> E[Data Quality and Freshness]
 E --> F[Technical Engine: M15 / M5 / M1]
 G[Official Economic Calendar] --> H[News and Event Ingestion]
 I[Global and Iranian News Sources] --> H
 H --> J[Deduplication and Corroboration]
 J --> K[Fundamental Context Engine]
 D --> L[Decision and Risk Gate]
 F --> L
 K --> L
 E --> L
 L --> M{Safe and Valid Setup?}
 M -->|No| N[WAIT / CLOSED / DATA WARNING]
 M -->|Yes| O[BUY or SELL + Risk Levels]
 N --> P[Localization: FA / EN / Bilingual]
 O --> P
 P --> Q[Telegram Message with Color and Evidence]
 Q --> R[Audit Log and Backtest Dataset]
```

## 9. Current implementation status (last known 2026-11-06)
- Repository: `GanjGoldTrader/ganj-gold-bot`; development branch: `codex/diagnostics-healthcheck`.
- PR #1 is open and draft, base `main`, current development work includes cache-freshness correction (see latest branch head in GitHub); not merged and production deployment not confirmed.
- PR changes: structured MarketAPI HTTP/network/timeout/response diagnostics; bounded error details and request IDs without logging API key; real `/status` XAUUSD health check; cache only successful LIVE health results for 30 seconds; better `/price` and `/candles` errors; README; tests; GitHub Actions.
- 22 unit tests are now defined, including four health-cache cases, six candle-order/continuity regressions, and malformed-row handling. The earlier successful Actions run #19 predates the candle-validation commits; CI must be checked on the current HEAD. GitHub Actions completed successfully for commit `c193ea7397da426f6fb25c2ffa6741536638bc3f` (run #16, pull_request event). Re-check CI after subsequent commits.
- 2026-11-05 runtime: `/price` returned Bid 4088.87, Ask 4089.20, spread 0.33, status MARKET_CLOSED, timestamp 2026-11-05T21:58:59.992Z. Not a live tradable quote.
- `/candles` returned complete M1/M5/M15 history. `/signal` safely returned WAIT because quote was not LIVE.
- MarketAPI key was active with scopes read:history, read:latest, read:metadata, read:ohlcv, read:symbols. Never save or repeat the secret.
- These are historical test observations, not current prices/status.

## 10. Roadmap
```mermaid
flowchart TD
 S[0. Preserve project state and master spec] --> A[1. Finish diagnostics and static review]
 A --> B[2. Validate live price, candles, session status]
 B --> C[3. Validate technical engine and signal safety]
 C --> D[4. Define and test entry, stop, target, expiry]
 D --> E[5. Implement signal colors and confidence display]
 E --> F[6. Implement provider-specific market calendar]
 F --> G[7. Connect economic calendar and primary news sources]
 G --> H[8. Build verification and fundamental context]
 H --> I[9. Integrate technical + fundamental risk decision]
 I --> J[10. Add Persian / English / bilingual localization]
 J --> K[11. Backtest and walk-forward validation]
 K --> L[12. Paper observation and controlled release]
```

| Phase | Work | Status |
|---|---|---|
| 0 | Master spec and archive | In progress |
| 1 | Diagnostics, tests, static review | PR #1; review ongoing |
| 2 | Live runtime validation during open session | Pending |
| 3 | M15/M5/M1 technical validation | Pending |
| 4 | Entry/SL/TP/validity and risk/reward rules | To design/test |
| 5 | Signal colors/confidence presentation | Proposed |
| 6 | Provider-specific market calendar/reopening alerts | Proposed |
| 7 | Economic calendar/news ingestion | Proposed |
| 8 | News corroboration/fundamental interpretation | Proposed |
| 9 | Technical/fundamental decision integration | Proposed |
| 10 | Persian/English/bilingual messages | Proposed |
| 11 | Backtest/out-of-sample/walk-forward validation | Pending |
| 12 | Paper observation and controlled release | Pending |

## 11. Test and release gates
- Review complete PR diff and current CI; verify secrets never enter logs or commits.
- Test LIVE, stale quote, closed session, daily break, holiday, DST boundary, API timeout, 401/403/429/5xx, malformed JSON, missing/incomplete candles, and rate limits.
- In an open session verify `/status`, `/price`, `/candles`, `/signal`; confirm WAIT on unsafe data.
- Confirm no automatic trade execution.
- Backtest with realistic spread, slippage, fees, latency, chronological splits, walk-forward and out-of-sample testing. Report sample size, expectancy, drawdown, profit factor, and cost sensitivity. Paper-observe before performance claims.

## 12. Project archive / decision log (newest first)
### 2026-11-06 — Cached quote freshness correction
- Static review found that a cached LIVE health result reused its original quote-age value, which could understate the true age of the quote.
- Updated `get_health_status()` to recompute quote age on every cache hit and discard/refetch a cached quote once it exceeds the configured freshness limit.
- Added two regression tests: cached quote age is recalculated; a cached quote that has aged out is fetched again.
- Code and tests committed on `codex/diagnostics-healthcheck`; latest known commit: `7a729e1e89494dfc395e6d81fba167abea62e7fc`. CI was queued/in progress when this note was written.
- Status: implemented on development branch; CI passed for the documented commit; runtime validation remains pending. No signal rules changed.

### 2026-11-06 — Permanent project archive requested
- Owner requested a durable repository document to preserve all prior and future agreements, features, roadmap and flowcharts across chats.
- Owner requested a closing routine: archive new decisions, requirements and work items at the end of each substantial project conversation.
- Added proposed color semantics, news/fundamental subsystem, multi-source corroboration, economic calendar, provider-specific session calendar/reopening notice, and Persian/English/bilingual UX.
- Status: recorded in roadmap; these features are not yet implemented.

### 2026-11-05 — MarketAPI runtime validation
- `/price` and `/candles` reached MarketAPI. Quote status was MARKET_CLOSED and timestamp was not live; do not treat as tradable.
- Complete M1/M5/M15 candles were returned. `/signal` correctly returned WAIT due to non-LIVE price.

### 2026-11-05 — Health-check cache correction
- Only successful LIVE health results are cached for 30 seconds; closed/stale results are rechecked.
- Added tests for LIVE caching and closed-market non-caching. Latest known PR workflow passed.

### 2026-11-05 — Diagnostics PR
- PR #1 created on `codex/diagnostics-healthcheck`; diagnostics, health check, README, tests and CI added.
- Signal logic unchanged. PR remains draft/open; not merged/deployed.



### 2026-11-06 — UTC candle ordering and recent continuity guard
- Re-read the live branch archive, PR #1, complete PR diff, main.py, and tests/test_main.py before continuing. PR #1 remains open/draft, base main, not merged. Initial observed HEAD was 1c51ed13f7ab1decdd45669e74602e45a24cfdb6; Actions run #19 was successful for that pre-change commit.
- Confirmed the previously identified weaknesses were still present: get_candles() sorted raw timestamp strings; duplicate UTC instants were not rejected; check_freshness() iterated only supplied timeframes and did not require M1/M5/M15 or validate recent continuity.
- Updated get_candles() to parse timestamps to UTC-aware datetimes, sort by actual instant, and reject duplicate instants (including different offset representations of the same instant).
- Added validate_candle_sequence(candles, timeframe): requires a supported timeframe and at least three candles; requires strictly increasing timestamps and exact timeframe spacing among only the latest three candles. It intentionally does not reject older historical gaps, avoiding false failures across normal market closures.
- Updated check_freshness() to require M1, M5, and M15 and validate each recent sequence before freshness checks. No modulo/grid-alignment assumption was added because the provider documentation reviewed so far does not establish a fixed candle-boundary convention.
- Added six regression tests: UTC ordering across differing offsets; duplicate UTC instant rejection; recent M1 gap rejection; allowance for an older historical gap; exact M5 spacing; and missing required timeframe rejection.
- GitHub accepted both code updates on codex/diagnostics-healthcheck: main.py commit 5cd04ba8b9a295d7b21816d7d5f657260decd9d7; tests commit 4c568932bc8f73f880392fcfcd5edb4f32302141. Current test count is 21 (15 existing + 6 new).
- Status: code and regression tests committed to development branch; execution/CI validation on the new HEAD is pending. Do not merge or deploy. Existing CI success #19 applies only to the earlier commit.



### 2026-11-06 — Concurrent market snapshot and malformed candle-row resilience
- Re-checked Actions run #24 for commit 5647eb55b47ce7f09d08ce73875a5df0dc6c6242: completed successfully (compile and unit-test job green).
- Static review of Telegram handlers found that /signal created asyncio.to_thread coroutines but awaited them one by one, so the four MarketAPI requests were effectively sequential despite the user-facing message. Updated /signal to await the quote and three timeframe fetches together with asyncio.gather; updated /candles to fetch M1/M5/M15 concurrently as well.
- Hardened get_candles() to skip non-dictionary rows in otherwise valid provider arrays rather than aborting the whole candle response.
- Added one regression test for malformed non-object candle rows. Test count is now 22.
- Commits: handler/data robustness change 33f473eeb7f6fe735ba58f831a8a19434216f083; regression test 4ba3fdb15501d274e035a7ac86c426de3e115d32.
- Status: changes committed to development branch; CI on the latest HEAD is pending. No production deployment, merge, or automatic trade execution has been performed.

## 13. Open decisions
- Confirm exact broker/provider behind MarketAPI XAUUSD and its current official session calendar.
- Choose display timezone preference; UTC remains canonical.
- Select news/calendar feeds after checking API access, reliability, licensing, latency, and cost.
- Define event-risk windows using tests, not guesses.
- Calibrate confidence tiers from backtests.
- Finalize entry/stop/target/expiry rules; decide whether target adapts to ATR and spread.
- Confirm Persian default vs selectable language mode (recommended: selectable, Persian initial default).

## 14. Next actions
1. Review PR #1 diff and current CI; keep unmerged pending runtime validation.
2. Validate `/status`, `/price`, `/candles`, `/signal` during a confirmed open session.
3. Identify the actual MarketAPI underlying quote source and official session calendar.
4. Design a stable technical signal/risk output schema before changing signal logic.
5. Implement and test calendar/session handling and color/status rendering.
6. Evaluate economic calendar and news providers; build source adapters and corroboration.
7. Add localization templates without changing analytical calculations.
8. Update this archive at the end of every substantial project conversation.