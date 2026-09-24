import datetime
import json
import threading
from pathlib import Path

# Resolved from this file rather than the process's working directory, so the
# counter lands in the same place no matter where the app is started from.
QUOTA_FILE = Path(__file__).resolve().parent.parent / ".daily_quota.json"


class PersistentDailyQuotaTracker:
    """
    Shared, persistent daily quota tracker backed by a local JSON file.
    The lock stops parallel calls (e.g. hybrid's vector + graph threads)
    from overwriting each other's increment.
    """
    def __init__(self, state_file=".daily_quota.json", max_rpd: int = 250):
        self.state_file = Path(state_file)
        self.max_rpd = max_rpd
        self._lock = threading.Lock()

    def _load_state(self) -> int:
        today_str = datetime.date.today().isoformat()
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                if data.get("date") == today_str:
                    return data.get("count", 0)
            except Exception:
                pass
        return 0

    def _save_state(self, count: int):
        today_str = datetime.date.today().isoformat()
        self.state_file.write_text(json.dumps({"date": today_str, "count": count}))

    def check_and_increment(self):
        with self._lock:
            current_count = self._load_state()
            if current_count >= self.max_rpd:
                raise RuntimeError(
                    f"Daily Quota Guardrail Triggered: Max daily limit of {self.max_rpd} "
                    f"requests reached ({current_count}/{self.max_rpd}). Resets tomorrow."
                )
            new_count = current_count + 1
            self._save_state(new_count)
        print(f"[Shared Daily Quota] Total requests used today: {new_count}/{self.max_rpd}")


daily_limiter = PersistentDailyQuotaTracker(state_file=QUOTA_FILE, max_rpd=250)
