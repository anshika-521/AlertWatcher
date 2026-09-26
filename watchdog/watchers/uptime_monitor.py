"""Watcher: alerts when a URL goes down, comes back up, or its content changes."""
import hashlib
from typing import Any, Optional

import requests

from watchdog.watcher_base import Watcher, WatchResult


class UptimeMonitorWatcher(Watcher):
    """config: {"url": str, "watch_content": bool, "timeout": int}

    Alerts on status flip (up<->down) always. If watch_content is true,
    also alerts when the response body's hash changes while the site stays up.
    """

    def fetch(self, last_state: Optional[dict[str, Any]]) -> WatchResult:
        url = self.config["url"]
        timeout = self.config.get("timeout", 10)
        watch_content = self.config.get("watch_content", False)

        is_up, status_code, content_hash = self._check(url, timeout, watch_content)

        state: dict[str, Any] = {"is_up": is_up, "status_code": status_code}
        if watch_content:
            state["content_hash"] = content_hash

        alert_message = self._check_alert(url, state, last_state, watch_content)
        return WatchResult(state=state, alert_message=alert_message)

    def _check(self, url: str, timeout: int, watch_content: bool):
        try:
            resp = requests.get(url, timeout=timeout)
            is_up = resp.status_code < 500
            content_hash = None
            if watch_content and is_up:
                content_hash = hashlib.sha256(resp.content).hexdigest()
            return is_up, resp.status_code, content_hash
        except requests.RequestException:
            return False, None, None

    def _check_alert(self, url, state, last_state, watch_content) -> Optional[str]:
        if last_state is None:
            return None

        was_up = last_state.get("is_up")
        is_up = state.get("is_up")

        if was_up and not is_up:
            return f"{url} is DOWN (status: {state.get('status_code')})."
        if not was_up and is_up:
            return f"{url} is back UP."

        if watch_content and is_up and was_up:
            old_hash = last_state.get("content_hash")
            new_hash = state.get("content_hash")
            if old_hash and new_hash and old_hash != new_hash:
                return f"{url} content changed (hash {new_hash[:8]})."

        return None
