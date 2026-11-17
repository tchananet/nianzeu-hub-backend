import pytest

from app.core.origins import is_allowed_origin, normalize_origin, usable_origin

CONFIGURED = "https://app.example.com"
ALLOWED = (CONFIGURED,)


@pytest.mark.parametrize("value", [
    CONFIGURED, "HTTPS://APP.EXAMPLE.COM", "https://app.example.com:443",
])
def test_the_configured_origin_is_trusted_however_it_is_spelled(value: str) -> None:
    assert is_allowed_origin(value, "production", ALLOWED)


@pytest.mark.parametrize("value", [
    # Any other host, including a subdomain or parent of the configured one: no domain
    # is trusted implicitly, which is the whole point of pinning.
    "https://evil.example.com", "https://app.example.com.evil.test",
    "https://sub.app.example.com", "https://example.com", "https://appexample.com",
    # Shape failures the normaliser rejects outright.
    "null", "https://app.example.com/", "https://app.example.com?",
    "https://app.example.com#", "https://app.example.com.", "https://app.example.com:",
    "https://user@app.example.com", "https://%61pp.example.com",
    "https://app.example.com https://evil.test",
    # Right host, wrong scheme or port.
    "http://app.example.com", "https://app.example.com:444",
])
def test_everything_else_is_refused(value: str) -> None:
    assert not is_allowed_origin(value, "production", ALLOWED)


def test_without_a_configured_origin_nothing_is_trusted() -> None:
    # A caller that forgets to pass the configured origins must fail closed.
    assert not is_allowed_origin(CONFIGURED, "production")
    assert not is_allowed_origin(CONFIGURED, "production", None)
    assert not is_allowed_origin(CONFIGURED, "production", ())


@pytest.mark.parametrize("port", ["", ":1", ":80", ":3000", ":65535"])
def test_localhost_is_a_development_convenience_only(port: str) -> None:
    value = "http://localhost" + port
    assert is_allowed_origin(value, "test", ALLOWED)
    assert is_allowed_origin(value, "local", ALLOWED)
    assert not is_allowed_origin(value, "production", ALLOWED)


@pytest.mark.parametrize("value", [
    "http://127.0.0.1", "http://[::1]", "http://a.localhost", "http://localhost:0",
    "http://localhost:65536",
])
def test_lookalike_loopback_origins_are_not_localhost(value: str) -> None:
    assert not is_allowed_origin(value, "test", ALLOWED)


@pytest.mark.parametrize("value", [
    "https://app.example.com", "https://nianzeu.example.org", "https://a.b.c.example",
])
def test_any_https_host_may_be_configured(value: str) -> None:
    # The deployment chooses its own domain; the code holds no list of names.
    assert usable_origin(value, "production") == value.rstrip("/")


def test_a_configured_origin_is_normalised() -> None:
    assert usable_origin("HTTPS://APP.EXAMPLE.COM:443", "production") == CONFIGURED
    assert usable_origin("http://LOCALHOST:80", "test") == "http://localhost"


@pytest.mark.parametrize(("value", "environment"), [
    ("http://app.example.com", "production"),
    ("http://localhost:3000", "production"),
    ("https://app.example.com:8443", "production"),
    ("ftp://app.example.com", "production"),
    ("https://app.example.com/path", "production"),
    ("not-an-origin", "test"),
])
def test_an_unusable_configured_origin_is_refused_at_boot(value: str, environment: str) -> None:
    with pytest.raises(ValueError):
        usable_origin(value, environment)


def test_normalisation_drops_the_default_port_and_lowercases_the_host() -> None:
    assert normalize_origin("HTTPS://A.EXAMPLE.COM:443") == "https://a.example.com"
    assert normalize_origin("http://LOCALHOST:80") == "http://localhost"
