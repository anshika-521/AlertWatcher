# Watchdog

A pluggable monitoring and alerting platform. Each **watcher** polls one
external data source on its own schedule — a REST API, a scraped web page,
anything with a `fetch()`. The core engine diffs the result against
last-seen state, evaluates alert rules, dedups repeat alerts, and dispatches
notifications to Telegram with retry/backoff on delivery failure.

Adding a new data source is one `Watcher` subclass — the scheduler, storage,
dedup, and alerting are all shared, unchanged.

## Live watchers

| Watcher | Source type | Triggers on |
|---|---|---|
| `github_release.py` | REST API (GitHub) | New release published on a tracked repo |
| `price_tracker.py` | HTML scrape (BeautifulSoup) | Price drops below a threshold, or by a % since last check |
| `uptime_monitor.py` | HTTP polling + content hashing | Site goes down / comes back up, or its content changes |

All three were validated against real, live data end to end through
Telegram — a real GitHub release, a real scraped price drop, and a real
content change on an external site each fired a real alert.

## Architecture

```
watchdog/
├── watcher_base.py   # plugin interface: fetch(last_state) -> WatchResult
├── engine.py         # scheduler, diffing, dedup, retry/backoff dispatch
├── store.py          # SQLite: last-seen state per watcher + alert history
├── dispatcher.py      # Telegram Bot API integration
└── watchers/          # one module per data source
```

`api.py` serves a minimal read-only dashboard (watcher status + alert
history) via FastAPI — no build step, no frontend framework.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID

python main.py                                    # starts the alert engine
uvicorn api:app --reload --port 8000              # starts the dashboard (optional, separate process)
```

Get a bot token from [@BotFather](https://t.me/BotFather) on Telegram, message
your bot once, then call `https://api.telegram.org/bot<TOKEN>/getUpdates` to
find your chat ID.

## Tests

```bash
python -m pytest tests/ -v
```
