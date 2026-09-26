"""Watcher: alerts when a GitHub repo publishes a new release."""
from typing import Any, Optional

import requests

from watchdog.watcher_base import Watcher, WatchResult


class GithubReleaseWatcher(Watcher):
    """config: {"repo": "owner/name"}"""

    def fetch(self, last_state: Optional[dict[str, Any]]) -> WatchResult:
        repo = self.config["repo"]
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/releases/latest",
            headers={"Accept": "application/vnd.github+json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        latest_tag = data.get("tag_name")
        release_url = data.get("html_url")

        state = {"latest_tag": latest_tag}
        alert_message = None

        if last_state is not None and last_state.get("latest_tag") != latest_tag:
            alert_message = f"New release for {repo}: {latest_tag} ({release_url})"

        return WatchResult(state=state, alert_message=alert_message)
