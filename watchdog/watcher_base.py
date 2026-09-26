"""Common interface every watcher plugin implements."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class WatchResult:
    """What a watcher's fetch() returns each poll cycle."""
    state: dict[str, Any]          # arbitrary snapshot to diff against last-seen state
    alert_message: Optional[str] = None  # set if this cycle should trigger an alert


class Watcher(ABC):
    """Base class for all watcher plugins.

    A watcher owns exactly one external data source. The engine calls
    fetch() on a schedule, diffs the returned state against the last
    persisted state for this watcher, and dispatches an alert when
    alert_message is set.
    """

    def __init__(self, name: str, config: dict[str, Any]):
        self.name = name
        self.config = config

    @abstractmethod
    def fetch(self, last_state: Optional[dict[str, Any]]) -> WatchResult:
        """Fetch current state, compare with last_state, decide if alert is needed.

        last_state is None on the very first run for this watcher.
        """
        raise NotImplementedError
