"""Telegram alert dispatch. Single integration point every watcher funnels through."""
import os
import requests


class TelegramDispatcher:
    def __init__(self, bot_token: str | None = None, chat_id: str | None = None):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
        if not self.bot_token or not self.chat_id:
            raise ValueError(
                "Telegram credentials missing. Set TELEGRAM_BOT_TOKEN and "
                "TELEGRAM_CHAT_ID env vars, or pass them explicitly."
            )
        self._api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send(self, message: str) -> None:
        resp = requests.post(
            self._api_url,
            json={"chat_id": self.chat_id, "text": message},
            timeout=10,
        )
        resp.raise_for_status()
