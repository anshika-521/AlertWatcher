"""Minimal read-only dashboard: watcher status + alert history."""
import json
from datetime import datetime, timezone
from html import escape

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from watchdog.store import Store

app = FastAPI()
store = Store("data/watchdog.db")

PAGE_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<title>Watchdog</title>
<meta http-equiv="refresh" content="10">
<style>
  :root {{ color-scheme: light dark; }}
  body {{
    font-family: -apple-system, Segoe UI, sans-serif;
    max-width: 860px; margin: 40px auto; padding: 0 20px;
    color: #1a1a1a; background: #fafafa;
  }}
  h1 {{ font-size: 24px; display: flex; align-items: center; gap: 10px; }}
  h1 .dot {{ width: 10px; height: 10px; border-radius: 50%; background: #2ecc71; display: inline-block; }}
  .subtitle {{ color: #888; font-size: 13px; margin-top: -8px; }}
  h2 {{ font-size: 15px; margin-top: 36px; color: #555; text-transform: uppercase; letter-spacing: 0.03em; }}
  .cards {{ display: grid; gap: 10px; margin-top: 10px; }}
  .card {{
    background: #fff; border: 1px solid #e5e5e5; border-radius: 8px;
    padding: 12px 16px; display: flex; justify-content: space-between; align-items: center;
    gap: 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.03);
  }}
  .card-left {{ display: flex; flex-direction: column; gap: 3px; min-width: 0; }}
  .watcher-name {{ font-weight: 600; font-size: 14px; }}
  .state-line {{ font-size: 12.5px; color: #666; font-family: ui-monospace, Consolas, monospace; overflow-wrap: anywhere; }}
  .updated {{ font-size: 11.5px; color: #999; white-space: nowrap; }}
  .status {{ font-size: 11px; font-weight: 600; padding: 3px 9px; border-radius: 12px; white-space: nowrap; }}
  .status-up {{ background: #e7f8ee; color: #1e8e4a; }}
  .status-down {{ background: #fdecea; color: #c0392b; }}
  .status-neutral {{ background: #eef1f6; color: #4a5568; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; background: #fff; border-radius: 8px; overflow: hidden; }}
  th, td {{ text-align: left; padding: 9px 12px; border-bottom: 1px solid #f0f0f0; font-size: 13.5px; }}
  th {{ color: #888; font-weight: 600; text-transform: uppercase; font-size: 10.5px; background: #f7f7f8; }}
  tr:last-child td {{ border-bottom: none; }}
  .empty {{ color: #999; font-size: 14px; padding: 14px; background: #fff; border-radius: 8px; border: 1px dashed #ddd; }}
  footer {{ margin-top: 40px; color: #bbb; font-size: 11px; }}
</style>
</head>
<body>
  <h1><span class="dot"></span>Watchdog</h1>
  <div class="subtitle">Pluggable monitoring &amp; alerting platform &middot; auto-refreshes every 10s</div>

  <h2>Watchers ({watcher_count})</h2>
  {watchers_cards}

  <h2>Recent Alerts ({alert_count})</h2>
  {alerts_table}

  <footer>SQLite-backed &middot; Telegram dispatch &middot; retry/backoff on delivery failure</footer>
</body>
</html>
"""


def _to_local(utc_str: str) -> str:
    """SQLite stores datetime('now') in UTC; render it in the server's local time zone."""
    try:
        dt_utc = datetime.strptime(utc_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        return dt_utc.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return utc_str


def _status_badge(state: dict) -> str:
    if "is_up" in state:
        if state["is_up"]:
            return '<span class="status status-up">UP</span>'
        return '<span class="status status-down">DOWN</span>'
    return '<span class="status status-neutral">OK</span>'


def _watchers_cards() -> str:
    rows = store.list_states()
    if not rows:
        return '<div class="empty">No watchers have reported state yet.</div>'

    cards = []
    for r in rows:
        try:
            state = json.loads(r["state_json"])
        except (json.JSONDecodeError, TypeError):
            state = {}
        state_line = ", ".join(f"{k}: {v}" for k, v in state.items())
        cards.append(
            f'<div class="card">'
            f'<div class="card-left">'
            f'<span class="watcher-name">{escape(r["watcher_name"])}</span>'
            f'<span class="state-line">{escape(state_line)}</span>'
            f'</div>'
            f'<div style="display:flex; align-items:center; gap:10px;">'
            f'{_status_badge(state)}'
            f'<span class="updated">{escape(_to_local(r["updated_at"]))}</span>'
            f'</div>'
            f'</div>'
        )
    return f'<div class="cards">{"".join(cards)}</div>'


def _alerts_table() -> str:
    alerts = store.recent_alerts(limit=50)
    if not alerts:
        return '<div class="empty">No alerts fired yet.</div>'
    body = "".join(
        f"<tr><td>{escape(a['watcher'])}</td><td>{escape(a['message'])}</td><td>{escape(_to_local(a['sent_at']))}</td></tr>"
        for a in alerts
    )
    return f"<table><tr><th>Watcher</th><th>Message</th><th>Sent At</th></tr>{body}</table>"


@app.get("/", response_class=HTMLResponse)
def dashboard():
    watcher_rows = store.list_states()
    alert_rows = store.recent_alerts(limit=50)
    return PAGE_TEMPLATE.format(
        watcher_count=len(watcher_rows),
        alert_count=len(alert_rows),
        watchers_cards=_watchers_cards(),
        alerts_table=_alerts_table(),
    )


@app.get("/api/alerts")
def api_alerts():
    return store.recent_alerts(limit=50)
