# Cursor implementation prompt — TradingEngineAI

Copy everything below the line into Cursor Agent mode when you are ready to build. The agent implements. It does not reopen product decisions that this file and the specification already close.

---

You are implementing TradingEngineAI in the Morning-algo repository.

Read these files before writing code, in this order:

1. `docs/TRADINGENGINEAI_SPECIFICATION.md` — source of truth for behaviour, schemas, math, licensing, and tests.
2. `buildOrder.md` — do the first phase whose status is not complete. Stop at the end of that phase unless the user asked you to continue.
3. `README.md`.

The repository started as a specification. Preserve every requirement in the specification. If this prompt and the specification disagree, follow the specification and mention the difference in the phase notes.

## Product

Build a production-quality private morning dashboard for the owning Zerodha account.

The owner uses it to see:

- Nifty 50 expected opening direction
- Sensex expected opening direction
- gap-up, gap-down, and flat heuristic scores
- global market description from licensed inputs
- GIFT Nifty movement
- an intraday bullish, bearish, or neutral label after the open
- opening range and VWAP confirmation

This is analytical decision support. It does not place, modify, or cancel orders. It does not call Kite order, GTT, or margin endpoints.

## Stack

- Frontend: Angular 22, TypeScript, Angular Material, TradingView Lightweight Charts 5.x, standalone components, SCSS.
- Backend: Python 3.12, FastAPI 0.162.x, Pydantic v2, async HTTP, WebSocket, Pandas and NumPy only where a calculation needs them. The heuristic in the specification is plain arithmetic and does not require a model library.
- Auth and storage: Firebase Authentication and Cloud Firestore, with `firebase-admin` on the server.
- Runtime: Docker, Docker Compose, Nginx, environment configuration.

Pin versions in lockfiles at implementation time.

## UI

Dark fintech dashboard, Asia/Kolkata everywhere the user looks.

Header: TradingEngineAI wordmark, ticking IST clock, session status from the configured timetable, data refresh time, socket status.

Market overview: GIFT Nifty price, change, and percent; Nifty 50 previous close; Nifty indicative pre-open only when `kind` is `vendor_indicative` or `exchange_published`; Sensex previous close and the same indicative rule.

Prediction cards: GREEN, RED, FLAT, or UNKNOWN; three heuristic scores; confidence; experimental badge; last calculated time. While `calibrated` is false, the visible label is “Experimental heuristic score. This is not a statistically validated probability.”

Global markets: Nasdaq, Dow Jones, S&P 500, Nikkei 225, Hang Seng, and the deterministic summary string from the API.

Trading bias: bullish, bearish, or neutral; CE, PE, or WAIT; the rule sentence; the risk warning from the specification. No order button and no control named Buy, Sell, or Place order.

Charts: GIFT Nifty movement, Nifty intraday candles, Sensex intraday candles, opening-range guides, VWAP, and volume when volume exists.

Timeline checkpoints: 05:15 GIFT session 1, 08:00 GIFT review, 08:30 global review, 09:00 NSE pre-open, 09:15 cash open, 09:30 opening-trend confirmation.

Components to create: Dashboard, MarketOverview, GiftNiftyCard, NiftyPredictionCard, SensexPredictionCard, GlobalMarkets, SentimentScore, IntradayBias, MarketChart, OpeningRange, VwapIndicator, MarketTimeline, DataSourceStatus.

## API

Implement:

- `GET /api/v1/market/overview`
- `GET /api/v1/market/gift-nifty`
- `GET /api/v1/market/global-indices`
- `GET /api/v1/market/pre-open`
- `GET /api/v1/predictions/latest`
- `GET /api/v1/predictions/history`
- `GET /api/v1/market/intraday`
- `GET /api/v1/market/opening-range`
- `GET /api/v1/market/vwap`
- `GET /api/v1/health`
- `WS /ws/market`

Use the Pydantic models, status enum, error envelope, and auth rules in the specification. A missing vendor returns HTTP 200 with `status: unavailable` and a null value. Do not invent a price. Swagger UI stays on `/docs`.

## Market data

Kite Connect, official `kiteconnect` SDK, server side only:

- Nifty 50, Sensex, and India VIX quotes where the key is entitled
- intraday index candles
- historical candles for opening range and VWAP
- instrument dump for tokens; fallback tokens only when the dump is down, and the dump wins when it loads

The paid Connect plan is ₹500 per API key per month and includes live WebSocket data and historical candles. The free Personal API includes neither. Map a Personal-plan permission error to `kite_plan_lacks_market_data`.

Kite market data is for this owner’s private dashboard. Store it only under that Firebase uid. Do not build a shared quote cache. Do not expose the API key, secret, or access token to Angular or to client-readable Firestore documents.

GIFT Nifty goes through `GiftNiftyProvider`. Default implementation: unconfigured and unavailable. Optional HTTP adapter for a licensed feed, with the JSON contract in the specification. Do not scrape.

Global indices go through `GlobalIndicesProvider` for the US cash close and for Nikkei 225 and Hang Seng. A provider failure leaves that index unavailable and leaves the rest of the dashboard up.

NSE regular pre-open starts at 09:00 IST. Normal trading starts at 09:15 IST. The opening print is the exchange result of pre-open discovery. The internal matching minute is the configured `PREOPEN_MATCHING_START` (default 09:10) because NSE’s public pages have not always shown the same cutover. GIFT session 1 default open is 05:15 IST after the 2 November 2026 NSE IX extension; keep it in configuration.

## Prediction

Create `app/services/prediction_engine.py` as specified: weights, clipping, renormalisation, score shares, confidence cap, worked example locked by tests.

Inputs: GIFT percent change, US cash performance, Asian performance, India VIX, previous closes, licensed pre-open indications, and the optional user overnight flag.

Outputs: direction, three scores, confidence, feature contributions.

Call the live output an experimental heuristic score until the calibration gate (120 sessions and Brier score at or below 0.22) is actually met. Do not add probability fields before that.

Opening gap, only from an official open:

`gap percent = (opening price - previous close) / previous close * 100`

Categories use `GAP_FLAT_ABS_PERCENT` (default 0.15). Document the value in configuration.

After 09:15, show the official open when it exists, compute the realised gap, track the 5-minute and 15-minute ranges, compute VWAP, and set CE, PE, or WAIT only by rule `or15_vwap_v1`. Zero index volume makes VWAP unavailable. Before 09:15 the options bias is WAIT.

## Firestore

User-scoped collections in the specification: `users`, `user_settings`, and per-user `predictions`, `market_snapshots`, `global_market_snapshots`, `intraday_analysis`, `provider_status`.

Prediction documents carry the fields in the specification, including `score_kind` and `data_quality`. Storage timestamps are UTC. The UI converts to IST. Ship rules and indexes. Client writes to prediction and snapshot paths are denied.

## Docker and security

Add `frontend/Dockerfile`, `backend/Dockerfile`, `docker-compose.yml`, `deploy/nginx.conf`, `.env.example`, and `.dockerignore`.

Include local and production build targets, health checks, log volume, env vars, and `unless-stopped`. Do not commit secrets.

Also include Firebase token checks, allowlist, rate limiting, CORS, socket authentication, input validation, and logs that omit credentials.

## Tests

Backend: pytest for the engine, providers, API errors, missing data, timezones, opening range, and VWAP.

Frontend: component tests for the experimental label, unavailable prices, the timeline, and the risk warning.

No test may call a live exchange or vendor.

## Docs during implementation

Update `README.md` with Firebase, Kite, provider, Docker, and test instructions as those phases complete. Update `buildOrder.md` when a phase’s acceptance checks pass.

## Order of work

1. Inspect the repo.
2. Implement the earliest incomplete phase in `buildOrder.md`.
3. Run that phase’s tests.
4. Update `buildOrder.md`.
5. Stop, unless the user asked for more than one phase.

## Hard requirements

- Leave a market value blank when the source is missing, stale for scoring, or unlicensed.
- Keep heuristic scores labeled experimental until the calibration gate passes on real stored sessions.
- Keep CE and PE as labels. Do not send orders.
- Keep Kite secrets on the server.
- Treat Kite quotes as the owner’s private data.
- Re-check the Zerodha plan page and the NSE and NSE IX timing pages before enabling a live provider, and write down any difference.
