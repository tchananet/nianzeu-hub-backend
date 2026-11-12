from collections.abc import Callable, Iterator
from contextlib import contextmanager
from threading import Lock

from app.shared.errors import AppError


class Slots:
    """Per-instance bound for validation and download fan-out; excess fails with 503."""

    def __init__(self, capacity: int, overflow: Callable[[], AppError]) -> None:
        if capacity < 1:
            raise ValueError("Positive capacity required")
        self.capacity, self.overflow = capacity, overflow
        self.guard, self.used = Lock(), 0

    def acquire(self) -> None:
        with self.guard:
            if self.used >= self.capacity:
                raise self.overflow()
            self.used += 1

    def release(self) -> None:
        with self.guard:
            if self.used < 1:
                raise RuntimeError("Slot released twice")
            self.used -= 1

    @contextmanager
    def hold(self) -> Iterator[None]:
        self.acquire()
        try:
            yield
        finally:
            self.release()
