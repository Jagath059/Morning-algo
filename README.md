# Morning-algo

TradingEngineAI is a personal, analytical morning dashboard for Indian index sentiment. It describes an expected Nifty 50 and Sensex opening tone before 09:15 IST and, after the cash open, an opening-range and VWAP confirmation. It is decision support for the account owner. It does not place orders.

This repository currently holds the implementation specification. Application code starts from [buildOrder.md](buildOrder.md).

## Read these first

| Document | Role |
| --- | --- |
| [docs/TRADINGENGINEAI_SPECIFICATION.md](docs/TRADINGENGINEAI_SPECIFICATION.md) | Source of truth: architecture, contracts, prediction math, licensing, security, and tests |
| [docs/CURSOR_IMPLEMENTATION_PROMPT.md](docs/CURSOR_IMPLEMENTATION_PROMPT.md) | Copy-paste prompt for a Cursor agent that will implement the spec |
| [buildOrder.md](buildOrder.md) | Milestone order. Update it at the end of every completed milestone |

## Product boundary

The dashboard may show an indicative opening tone before 09:15 IST. The cash opening price is the exchange print after pre-open price discovery. NSE regular pre-open begins at 09:00 IST and normal trading begins at 09:15 IST. A heuristic score stays labeled **Experimental** until the calibration gate in the specification is met.

Kite Connect market data is for the owning Zerodha client’s private use. The paid Connect plan (₹500 per API key per month, as published by Zerodha) includes live WebSocket data and historical candles. The free Personal API does not. Quotes from Kite are not a data feed for other people.

## Stack the implementation will use

Angular 22, Angular Material, TradingView Lightweight Charts, Python 3.12, FastAPI, Pydantic, Firebase Authentication, Cloud Firestore, Docker, and Nginx.
