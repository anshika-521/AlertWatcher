import logging

from dotenv import load_dotenv

from watchdog.dispatcher import TelegramDispatcher
from watchdog.engine import Engine
from watchdog.store import Store
from watchdog.watchers.github_release import GithubReleaseWatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> None:
    load_dotenv()
    store = Store("data/watchdog.db")
    dispatcher = TelegramDispatcher()
    engine = Engine(store=store, dispatcher=dispatcher)

    engine.register(
        GithubReleaseWatcher(name="github:nodejs/node", config={"repo": "nodejs/node"}),
        interval_seconds=60,
    )

    engine.run_forever(poll_interval_seconds=15)


if __name__ == "__main__":
    main()
