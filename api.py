"""Minimal read-only dashboard: watcher status + alert history."""
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
  body {{ font-family: -apple-system, Segoe UI, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #1a1a1a; }}
  h1 {{ font-size: 22px; }}
  h2 {{ font-size: 16px; margin-top: 32px; color: #444; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #eee; font-size: 14px; }}
  th {{ color: #888; font-weight: 600; text-transform: uppercase; font-size: 11px; }}
  .empty {{ color: #999; font-size: 14px; padding: 12px 0; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; background: #eef; font-size: 12px; }}
</style>
</head>
<body>
  <h1>Watchdog</h1>
  <h2>Watchers</h2>
  {watchers_table}
  <h2>Recent Alerts</h2>
  {alerts_table}
</body>
</html>
"""


def _watchers_table() -> str:
    rows = store.list_states() if hasattr(store, "list_states") else []
    if not rows:
        return '<div class="empty">No watchers have reported state yet.</div>'
    body = "".join(
        f"<tr><td>{r['watcher_name']}</td><td><span class='badge'>{r['state_json']}</span></td><td>{r['updated_at']}</td></tr>"
        for r in rows
    )
    return f"<table><tr><th>Watcher</th><th>Last State</th><th>Updated</th></tr>{body}</table>"


def _alerts_table() -> str:
    alerts = store.recent_alerts(limit=50)
    if not alerts:
        return '<div class="empty">No alerts fired yet.</div>'
    body = "".join(
        f"<tr><td>{a['watcher']}</td><td>{a['message']}</td><td>{a['sent_at']}</td></tr>"
        for a in alerts
    )
    return f"<table><tr><th>Watcher</th><th>Message</th><th>Sent At</th></tr>{body}</table>"


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return PAGE_TEMPLATE.format(
        watchers_table=_watchers_table(),
        alerts_table=_alerts_table(),
    )


@app.get("/api/alerts")
def api_alerts():
    return store.recent_alerts(limit=50)
