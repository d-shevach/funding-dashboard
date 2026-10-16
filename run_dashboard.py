#!/usr/bin/env python3
"""Run Flask dashboard"""

from src.config import Config
from src.database import DatabasePool
from src.web.app import app

if __name__ == "__main__":
    Config.validate()
    DatabasePool.initialize()

    print("=" * 80)
    print("FUND ACCOUNTING - Dashboard")
    print("=" * 80)
    print("\nStarting Flask at http://localhost:5000")
    print("Press CTRL+C to stop\n")

    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
