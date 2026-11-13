# TradingEngineAI build order

A local dashboard and API now run with unconfigured market feeds. The source of truth for behaviour is [docs/TRADINGENGINEAI_SPECIFICATION.md](docs/TRADINGENGINEAI_SPECIFICATION.md). Phases below stay open until every acceptance check in that phase is met. The runnable shell covers the visible dashboard, the REST and WebSocket routes, and the heuristic engine. Firebase, live Kite quotes, licensed GIFT and global adapters, Docker, and calibration are still ahead.

Update this file at the end of every completed milestone: set the status, record the date in `YYYY-MM-DD`, and list the commits or pull requests that finished it. Leave later milestones untouched.

Market facts the schedule depends on are dated in the specification (checked 2026-11-13). Re-check the NSE, NSE IX, and Zerodha pages cited there before Phase 4 and Phase 5, because session clocks and API plan names change by circular.

## Milestone status

| Phase | Deliverable | Status | Completed |
| --- | --- | --- | --- |
| 0 | Implementation specification, agent prompt, this build order | Complete | 2026-11-13 |
| 1 | Angular dashboard UI with fixture states | Not started | |
| 2 | FastAPI backend, schemas, errors, health | Not started | |
| 3 | Firebase authentication, Firestore, security rules | Not started | |
| 4 | Kite Connect integration for the owning account | Not started | |
| 5 | GIFT Nifty and global-index providers | Not started | |
| 6 | Prediction engine and persistence | Not started | |
| 7 | Live updates, charts, opening range, VWAP | Not started | |
| 8 | Docker deployment | Not started | |
| 9 | Historical backtesting and calibration gate | Not started | |

## Phase 1 — Angular dashboard UI

Build the dark enterprise shell and every component named in the specification. Data comes from an in-memory fixture adapter that the UI labels as fixture data. Production builds cannot use that adapter.

Acceptance:

- Header shows the TradingEngineAI name, a ticking Asia/Kolkata clock, session status from the configured timetable, refresh time, and connection status.
- Overview, prediction, global, bias, chart, opening-range, VWAP, timeline, and source-status regions render for `ok`, `unavailable`, and `stale` quote states.
- Unavailable cards show the reason and leave the price blank. They never display a stand-in number.
- The prediction card says Experimental and “heuristic score”.
- The bias card shows the standing risk sentence. CE, PE, and WAIT are labels. There is no order button.
- Layout is usable at 1280px and at 390px width.
- Component tests cover session status, unavailable quotes, and the experimental label.

## Phase 2 — FastAPI backend

Create the Python service, Pydantic models, the ten REST routes, and `/ws/market`. Providers return unavailable until later phases. Swagger UI is served by FastAPI.

Acceptance:

- Every route validates inputs and returns the error envelope from the specification.
- A missing provider produces HTTP 200 with `status: unavailable` on that field. One failed provider still returns the rest of the payload.
- `/api/v1/health` returns no secrets.
- Tests cover the error envelope, partial payloads, and Asia/Kolkata trading-date boundaries, including the DST-neutral US-close dating rule.
- Default configuration cannot enable the fixture provider.

## Phase 3 — Firebase authentication and storage

Wire Angular sign-in, FastAPI verification of Firebase ID tokens, user-scoped Firestore documents, rules, and indexes.

Acceptance:

- Anonymous and wrong-project tokens receive 401.
- A uid outside `ALLOWED_UIDS` receives 403 when the allowlist is set.
- Client SDK writes to predictions, snapshots, and provider status fail under the rules.
- Broker fields are rejected by rules and by the server model.
- Timestamps stored in Firestore are UTC. The UI converts them to IST.

## Phase 4 — Kite Connect

Add the official `kiteconnect` SDK behind `KiteMarketDataProvider`, the daily instrument dump, historical candles, and a server-side request-token exchange. Order routes stay unwired.

Acceptance:

- API key, secret, and access token exist only in server environment or server-side storage.
- Personal (free) keys surface `kite_plan_lacks_market_data` and no prices.
- Paid-key quote, candle, opening-range, and VWAP paths are covered with recorded fixtures in tests.
- Instrument tokens come from the dump. The documented fallback tokens lose when the dump disagrees.
- A quote older than its stale threshold is `stale` and is not passed to the scorer as fresh.

## Phase 5 — GIFT Nifty and global providers

Add `GiftNiftyProvider` and `GlobalIndicesProvider` with an unconfigured default and one licensed HTTP adapter each. US names are the latest completed cash close when India is in the morning. Nikkei 225 and Hang Seng follow their own sessions.

Acceptance:

- Unset credentials produce `unavailable` and a visible source status.
- Provider exceptions are logged without secrets and do not fail `/market/overview`.
- Tests use static vendor payloads. No test calls a live vendor.
- The HTTP adapter rejects payloads that fail freshness or schema checks.

## Phase 6 — Prediction engine

Implement `app/services/prediction_engine.py` exactly as specified: weighted features, renormalisation when inputs are missing, heuristic scores, confidence cap, and the experimental label.

Acceptance:

- Unit tests lock the worked example in the specification to two decimal places.
- A full-data bullish case, a bearish case, a flat case, an all-missing case, and a single-feature case are tested.
- The all-missing case returns direction `UNKNOWN`, null scores, and confidence 0.
- API responses use `gap_up_score` while `calibrated` is false. They do not add probability fields.
- Each run can be stored under the signed-in user. Explanations list the features that actually contributed.

## Phase 7 — Live updates and charts

Subscribe to Kite Ticker only for a paid session of the owning account. Fan a one-second sanitized snapshot to that user’s `/ws/market`. Render Lightweight Charts for GIFT movement and cash-session candles, with opening-range guides and VWAP when volume is usable.

Acceptance:

- The socket closes on an invalid or expired Firebase token.
- A second socket for the same uid replaces the first.
- Index candles with zero volume leave VWAP `unavailable`.
- Before 09:15 the options bias is `WAIT`. After the configured confirmation rule, it becomes `CE`, `PE`, or `WAIT` with the rule id in the payload.
- The UI replaces expected open fields with the actual open when `open_status` is `official`.

## Phase 8 — Docker deployment

Add Dockerfiles, Compose, Nginx, `.env.example`, and `.dockerignore`.

Acceptance:

- `docker compose up` serves the UI and proxies `/api` and `/ws`.
- Backend and frontend images pass their health checks.
- The image build context excludes `.env`, service accounts, and token files.
- README sections exist for local compose, production env vars, logs, and restart policy.

## Phase 9 — Backtesting and calibration

Offline job only. It replays stored inputs against later official opens and writes a report. It changes `score_kind` only when the calibration gate passes.

Acceptance:

- The report includes sample size, hit rate, and Brier score by instrument.
- Below 120 samples, or with Brier score above 0.22, the live API stays `experimental_heuristic`.
- The job has no order-placement dependency.
- Thresholds and weights remain configuration. The report does not silently edit them.

## Working agreement for every phase

1. Read the specification section for that phase before editing.
2. Keep existing behaviour working.
3. Add tests in the same milestone as the behaviour.
4. Leave market numbers empty when the source is missing.
5. Update this file when the milestone’s acceptance checks pass.
