"""Reuse loaded model artifacts, invalidating the cache when retraining replaces them."""
from functools import lru_cache
from pathlib import Path
from threading import Lock
import joblib

_lock = Lock()

@lru_cache(maxsize=2)
def _load(path: str, modified: int, size: int):
    return joblib.load(path)

def load_model(path: str = "fitness_ranker.pkl"):
    artifact = Path(path).resolve()
    with _lock:
        stat = artifact.stat()
        return _load(str(artifact), stat.st_mtime_ns, stat.st_size)
