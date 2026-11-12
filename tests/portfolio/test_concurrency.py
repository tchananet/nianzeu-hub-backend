import pytest

from app.modules.portfolio.concurrency import Slots
from app.modules.portfolio.errors import validation_busy
from app.shared.errors import AppError


def test_capacity_is_enforced_and_released() -> None:
    slots = Slots(2, validation_busy)
    with slots.hold(), slots.hold():
        with pytest.raises(AppError) as error:
            slots.acquire()
        assert (error.value.code, error.value.status) == ("VALIDATION_BUSY", 503)
    assert slots.used == 0
    slots.acquire()
    slots.release()


def test_release_without_acquire_fails_loudly() -> None:
    slots = Slots(1, validation_busy)
    with pytest.raises(RuntimeError):
        slots.release()
    with pytest.raises(ValueError):
        Slots(0, validation_busy)
