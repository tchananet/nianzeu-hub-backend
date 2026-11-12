"""Run from the test container while parent stops/restores one dependency."""

import os
import sys
from time import monotonic, sleep

import httpx


def main():
    assert os.environ["APP_ENVIRONMENT"] == "test"
    assert os.environ["F02_STACK_TEST"] == "1"
    expected = sys.argv[1]
    assert expected in ("ready", "unavailable")
    base = os.environ["F02_API_URL"]
    deadline = monotonic() + 60
    while True:
        live = httpx.get(f"{base}/health/live", timeout=5)
        assert live.status_code == 200 and live.json() == {"status": "ok"}
        ready = httpx.get(f"{base}/health/ready", timeout=25)
        if expected == "unavailable":
            assert ready.status_code == 503
            assert ready.json()["error"] == {
                "code": "DEPENDENCY_UNAVAILABLE", "message": "Dependency unavailable",
                "details": [],
            }
            assert ready.json()["request_id"] == ready.headers["x-request-id"]
            break
        if ready.status_code == 200:
            assert ready.json() == {"status": "ready"}
            break
        assert monotonic() < deadline, "readiness did not recover"
        sleep(1)
    print(f"F02 health {expected}: PASS")


if __name__ == "__main__":
    main()
