"""Core engine: runs each watcher on its own interval, diffs state, dispatches alerts."""
import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Optional

from watchdog.dispatcher import TelegramDispatcher
from watchdog.store import Store
from watchdog.watcher_base import Watcher

logger = logging.getLogger("watchdog.engine")


@dataclass
class WatcherJob:
    watcher: Watcher
    interval_seconds: int
    _last_run: float = 0.0

    def due(self, now: float) -> bool:
        return now - self._last_run >= self.interval_seconds


class Engine:
    def __init__(self, store: Store, dispatcher: TelegramDispatcher):
        self.store = store
        self.dispatcher = dispatcher
        self.jobs: list[WatcherJob] = []

    def register(self, watcher: Watcher, interval_seconds: int) -> None:
        self.jobs.append(WatcherJob(watcher=watcher, interval_seconds=interval_seconds))

    def run_once(self) -> None:
        """Run every due watcher a single time. Called in a loop by run_forever, or
        directly for a one-shot / cron-triggered invocation."""
        now = time.time()
        for job in self.jobs:
            if not job.due(now):
                continue
            job._last_run = now
            self._run_job(job)

    def _run_job(self, job: WatcherJob) -> None:
        watcher = job.watcher
        last_state = self.store.get_state(watcher.name)
        try:
            result = watcher.fetch(last_state)
        except Exception:
            logger.exception("watcher %s failed", watcher.name)
            return

        self.store.set_state(watcher.name, result.state)

        if not result.alert_message:
            return

        dedup_key = self._dedup_key(result.alert_message)
        if self.store.already_alerted(watcher.name, dedup_key):
            logger.info("watcher %s: alert suppressed (duplicate)", watcher.name)
            return

        self._dispatch_with_retry(watcher.name, result.alert_message, dedup_key)

    def _dispatch_with_retry(self, watcher_name: str, message: str, dedup_key: str,
                              max_attempts: int = 3) -> None:
        backoff = 2
        for attempt in range(1, max_attempts + 1):
            try:
                self.dispatcher.send(f"[{watcher_name}] {message}")
                self.store.record_alert(watcher_name, message, dedup_key)
                return
            except Exception:
                logger.exception(
                    "alert dispatch failed for %s (attempt %d/%d)",
                    watcher_name, attempt, max_attempts,
                )
                if attempt < max_attempts:
                    time.sleep(backoff)
                    backoff *= 2

    @staticmethod
    def _dedup_key(message: str) -> str:
        return hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]

    def run_forever(self, poll_interval_seconds: int = 15) -> None:
        logger.info("engine starting, %d watcher(s) registered", len(self.jobs))
        while True:
            self.run_once()
            time.sleep(poll_interval_seconds)
