import os
from datetime import datetime

LOG_FILE = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "Frostplay",
    "perf_debug.log"
)

def log_perf(tag: str, detail: str = "") -> None:
    try:
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        msg = f"[{ts}] [{tag}] {detail}\n"
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg)
    except Exception:
        pass

def clear_perf_log() -> None:
    try:
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
    except Exception:
        pass
