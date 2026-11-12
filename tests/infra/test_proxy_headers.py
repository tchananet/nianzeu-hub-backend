"""Guards the client-address chain the per-IP quotas depend on.

With proxy headers disabled, ``request.client.host`` is the reverse proxy for every
visitor, so all per-IP quotas of http.md share one counter and the per-visitor view
deduplication merges every visitor into a single daily view.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def command_line() -> str:
    lines = (ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()
    return next(line for line in lines if line.startswith("CMD") and "uvicorn" in line)


def test_runtime_does_not_disable_proxy_headers() -> None:
    assert "--no-proxy-headers" not in command_line()


def test_runtime_serves_the_application_factory() -> None:
    # app.main must stay importable without configuration, so no module-level app.
    assert "--factory" in command_line()
    assert "app.main:create_app" in command_line()
    assert "app = create_app()" not in (ROOT / "app" / "main.py").read_text(encoding="utf-8")


def test_compose_requires_an_explicit_trusted_proxy() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "FORWARDED_ALLOW_IPS: ${FORWARDED_ALLOW_IPS:?required}" in compose
    # A wildcard would let any direct client forge its own address.
    assert "FORWARDED_ALLOW_IPS=*" not in (ROOT / ".env.example").read_text(encoding="utf-8")
