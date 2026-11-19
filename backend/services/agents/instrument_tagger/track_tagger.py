#!/usr/bin/env python3
"""Tail the InstrumentTagger Lambda's CloudWatch logs."""
import os
import signal
import sys
import time
from datetime import datetime

import boto3
from dotenv import load_dotenv

load_dotenv(override=True)

LOG_GROUP = os.getenv("TAGGER_LOG_GROUP", "/aws/lambda/trading-tagger")
REGION = os.getenv("DEFAULT_AWS_REGION", "us-east-1")


class TaggerLogTracker:
    def __init__(self) -> None:
        self.logs_client = boto3.client("logs", region_name=REGION)
        self.running = True
        self.last_ts = None
        signal.signal(signal.SIGINT, self._stop)

    def _stop(self, *_):
        print("\nStopping.")
        self.running = False
        sys.exit(0)

    def _fetch(self, start_ms: int):
        try:
            resp = self.logs_client.filter_log_events(
                logGroupName=LOG_GROUP, startTime=start_ms, limit=100
            )
            return resp.get("events", [])
        except Exception as exc:
            print(f"Error fetching logs: {exc}")
            return []

    def _format(self, event) -> str:
        ts = datetime.fromtimestamp(event["timestamp"] / 1000).strftime("%H:%M:%S.%f")[:-3]
        msg = event["message"].strip()
        if not msg:
            return ""
        if "ERROR" in msg or "Failed" in msg:
            color = "\033[91m"
        elif "WARNING" in msg:
            color = "\033[93m"
        elif "classif" in msg.lower():
            color = "\033[94m"
        else:
            color = "\033[0m"
        return f"{ts} {color}{msg}\033[0m"

    def track(self) -> None:
        print(f"Tailing {LOG_GROUP}")
        start_ms = int((time.time() - 60) * 1000)
        seen = set()
        while self.running:
            for ev in self._fetch(start_ms):
                eid = ev.get("eventId")
                if eid in seen:
                    continue
                seen.add(eid)
                line = self._format(ev)
                if line:
                    print(line)
                start_ms = max(start_ms, ev["timestamp"] + 1)
            time.sleep(2)


if __name__ == "__main__":
    TaggerLogTracker().track()