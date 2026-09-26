import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from watchdog.engine import Engine
from watchdog.store import Store
from watchdog.watcher_base import Watcher, WatchResult


class FakeDispatcher:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)


class FlipWatcher(Watcher):
    """Alerts once, second run onward reports the same value (no new alert)."""

    def fetch(self, last_state):
        state = {"value": "v2"}
        alert = None
        if last_state is not None and last_state.get("value") != state["value"]:
            alert = "value changed to v2"
        return WatchResult(state=state, alert_message=alert)


def make_engine(tmp_path):
    store = Store(str(tmp_path / "test.db"))
    dispatcher = FakeDispatcher()
    engine = Engine(store=store, dispatcher=dispatcher)
    return engine, dispatcher


def test_first_run_no_alert_but_state_saved(tmp_path):
    engine, dispatcher = make_engine(tmp_path)
    engine.register(FlipWatcher(name="w1", config={}), interval_seconds=0)

    engine.run_once()

    assert dispatcher.sent == []
    assert engine.store.get_state("w1") == {"value": "v2"}


def test_second_run_alerts_on_change(tmp_path):
    engine, dispatcher = make_engine(tmp_path)
    watcher = FlipWatcher(name="w1", config={})
    engine.register(watcher, interval_seconds=0)

    engine.store.set_state("w1", {"value": "v1"})  # simulate prior state
    engine.run_once()

    assert len(dispatcher.sent) == 1
    assert "value changed to v2" in dispatcher.sent[0]


def test_duplicate_alert_is_suppressed(tmp_path):
    engine, dispatcher = make_engine(tmp_path)
    watcher = FlipWatcher(name="w1", config={})
    engine.register(watcher, interval_seconds=0)

    engine.store.set_state("w1", {"value": "v1"})
    engine.run_once()  # fires alert, state now v2
    engine.store.set_state("w1", {"value": "v1"})  # force a re-diff scenario
    engine.run_once()  # same alert message -> should be deduped

    assert len(dispatcher.sent) == 1
