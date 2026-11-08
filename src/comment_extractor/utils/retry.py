from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def run_with_retry(fn: Callable[[], T], retries: int, base_delay: float) -> T:
    attempts = 0
    while True:
        try:
            return fn()
        except Exception:
            attempts += 1
            if attempts > retries:
                raise
            jitter = random.uniform(0.0, 0.5)
            time.sleep(base_delay * attempts + jitter)
