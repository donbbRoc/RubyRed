#!/usr/bin/env python3
"""
Scheduler that runs insert_sample_data.py every 1 hour.
Usage: python3 scheduled_insert.py
"""

import subprocess
import sys
import os
import time
from datetime import datetime

INTERVAL_SECONDS = 3600  # 1 hour
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(SCRIPT_DIR, "insert_sample_data.py")


def run_insert():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{timestamp}] Starting insert_sample_data.py ...")

    result = subprocess.run(
        [sys.executable, SCRIPT_PATH],
        cwd=SCRIPT_DIR,
    )

    status = "SUCCESS" if result.returncode == 0 else f"FAILED (exit code {result.returncode})"
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Run finished - {status}")
    return result.returncode


def main():
    print(f"Scheduler started. Will run insert_sample_data.py every {INTERVAL_SECONDS // 60} minutes.")
    print(f"Script path: {SCRIPT_PATH}")
    print("Press Ctrl+C to stop.\n")

    run_count = 0
    while True:
        run_count += 1
        print(f"{'=' * 60}")
        print(f"Run #{run_count}")
        print(f"{'=' * 60}")

        run_insert()

        next_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\nNext run in {INTERVAL_SECONDS // 60} minutes (sleeping until then)...")

        try:
            time.sleep(INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print(f"\nScheduler stopped after {run_count} run(s).")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScheduler stopped.")
        sys.exit(0)
