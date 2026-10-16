#!/usr/bin/env python3
"""Run scheduled price, FX and snapshot jobs without the desktop UI"""

import time

from src.config import Config
from src.database import DatabasePool
from src.automation.scheduler import AutomationScheduler


def main():
    Config.validate()
    DatabasePool.initialize()

    scheduler = AutomationScheduler()
    scheduler.start()

    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
