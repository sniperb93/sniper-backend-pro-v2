import os
import threading
from datetime import datetime, timezone

class SniperManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._since = None
        self._mode = os.getenv("SNIPER_MODE", "paper")

    def start(self):
        with self._lock:
            if not self._running:
                self._running = True
                self._since = datetime.now(timezone.utc).isoformat()
            return {"status": "running", "since": self._since, "mode": self._mode}

    def stop(self):
        with self._lock:
            self._running = False
            return {"status": "stopped"}

    def status(self):
        with self._lock:
            return {
                "status": "running" if self._running else "stopped",
                "since": self._since,
                "mode": self._mode,
            }

SNIPER_MANAGER = SniperManager()