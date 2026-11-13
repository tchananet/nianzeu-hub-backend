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


def test_the_image_can_apply_its_own_migrations() -> None:
    # Without these, an operator needs a host checkout and a throwaway container just
    # to run alembic against production (GAP-11).
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY alembic.ini" in dockerfile
    assert "COPY migrations ./migrations" in dockerfile


def test_an_override_puts_the_api_on_the_proxy_network() -> None:
    # A containerised proxy cannot reach the api's loopback publication (GAP-01), so a
    # shared network is offered as an opt-in override rather than changed by default.
    override = (ROOT / "ops" / "deploy" / "compose.proxy.yml").read_text(encoding="utf-8")
    assert "networks: [default, proxy]" in override
    assert "external: true" in override
    # The database and object storage must never be reachable from that network.
    assert "db:" not in override and "minio:" not in override
    base = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "proxy:" not in base  # the base stack declares no such network
