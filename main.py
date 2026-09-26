import logging

from dotenv import load_dotenv

from watchdog.dispatcher import TelegramDispatcher
from watchdog.engine import Engine
from watchdog.store import Store
from watchdog.watchers.github_release import GithubReleaseWatcher
from watchdog.watchers.price_tracker import PriceTrackerWatcher
from watchdog.watchers.uptime_monitor import UptimeMonitorWatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> None:
    load_dotenv()
    store = Store("data/watchdog.db")
    dispatcher = TelegramDispatcher()
    engine = Engine(store=store, dispatcher=dispatcher)

    engine.register(
        GithubReleaseWatcher(name="github:anshika-521/AlertWatcher", config={"repo": "anshika-521/AlertWatcher"}),
        interval_seconds=120,
    )
    engine.register(
        PriceTrackerWatcher(
            name="price:atomic-habits",
            config={
                "url": "https://www.bookswagon.com/book/atomic-habits/9781847941831",
                "threshold": None,
                "drop_pct": 5,
            },
        ),
        interval_seconds=300,
    )
    engine.register(
        UptimeMonitorWatcher(
            name="uptime:github-profile",
            config={"url": "https://github.com/anshika-521", "watch_content": True, "selector": ".p-name"},
        ),
        interval_seconds=30,
    )

    engine.run_forever(poll_interval_seconds=10)


if __name__ == "__main__":
    main()
