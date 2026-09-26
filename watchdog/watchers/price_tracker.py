"""Watcher: alerts when a product page's price drops below a threshold or by a percentage."""
import re
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

from watchdog.watcher_base import Watcher, WatchResult

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

PRICE_RE = re.compile(r'"price"\s*:\s*"?(\d+(?:\.\d+)?)"?')


class PriceTrackerWatcher(Watcher):
    """config: {"url": str, "threshold": float | None, "drop_pct": float | None}

    Alerts when the current price is <= threshold, or has dropped by at
    least drop_pct percent since the last-seen price (whichever configured).
    """

    def fetch(self, last_state: Optional[dict[str, Any]]) -> WatchResult:
        url = self.config["url"]
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()

        price = self._extract_price(resp.text)
        state = {"price": price}

        if price is None:
            return WatchResult(state=state, alert_message=None)

        alert_message = self._check_alert(price, last_state)
        return WatchResult(state=state, alert_message=alert_message)

    def _extract_price(self, html: str) -> Optional[float]:
        match = PRICE_RE.search(html)
        if match:
            return float(match.group(1))

        # fallback: look for a schema.org price meta/itemprop tag
        soup = BeautifulSoup(html, "lxml")
        tag = soup.find(attrs={"itemprop": "price"})
        if tag:
            value = tag.get("content") or tag.get_text()
            try:
                return float(re.sub(r"[^\d.]", "", value))
            except ValueError:
                return None
        return None

    def _check_alert(self, price: float, last_state: Optional[dict[str, Any]]) -> Optional[str]:
        threshold = self.config.get("threshold")
        if threshold is not None and price <= threshold:
            return f"Price is now ₹{price:.0f}, at or below your threshold of ₹{threshold:.0f}."

        drop_pct = self.config.get("drop_pct")
        if drop_pct is not None and last_state is not None:
            last_price = last_state.get("price")
            if last_price and last_price > 0:
                pct_change = (last_price - price) / last_price * 100
                if pct_change >= drop_pct:
                    return (
                        f"Price dropped {pct_change:.1f}% (₹{last_price:.0f} → ₹{price:.0f})."
                    )
        return None
