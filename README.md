# Watchdog

A pluggable monitoring/alerting platform. Each "watcher" polls one external
data source on its own schedule; the core engine diffs the result against
last-seen state, dedups repeat alerts, and dispatches notifications through
Telegram with retry/backoff on delivery failure.

## Architecture

- `watchdog/watcher_base.py` — plugin interface every watcher implements (`fetch(last_state) -> WatchResult`)
- `watchdog/engine.py` — scheduler, state diffing, dedup, retry/backoff dispatch
- `watchdog/store.py` — SQLite-backed state store + alert history
- `watchdog/dispatcher.py` — Telegram Bot API integration
- `watchdog/watchers/` — one module per data source

Adding a new data source means writing one `Watcher` subclass — the engine,
scheduler, storage, and alerting are all shared.

## Watchers

- `github_release.py` — alerts on a new GitHub release for a tracked repo

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
python main.py
```

Get a bot token from [@BotFather](https://t.me/BotFather) on Telegram, then
message your bot once and call
`https://api.telegram.org/bot<TOKEN>/getUpdates` to find your chat ID.

## Tests

```bash
python -m pytest tests/ -v
```
