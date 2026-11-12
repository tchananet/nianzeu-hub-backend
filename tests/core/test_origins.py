import pytest

from app.core.origins import is_allowed_origin, normalize_origin


@pytest.mark.parametrize("value", [
    "https://diddifree.com", "https://a.b.diddifree.com", "https://netatroniks.xyz",
    "HTTPS://DIDDIFREE.COM:443",
])
def test_https_allowlist(value: str) -> None:
    assert is_allowed_origin(value, "production")


@pytest.mark.parametrize("value", [
    "null", "https://diddifree.com/", "https://diddifree.com?", "https://diddifree.com#",
    "https://diddifree.com.", "https://diddifree.com:", "https://user@diddifree.com",
    "https://diddifree.com.evil.test", "https://evildiddifree.com", "https://diddifre.com",
    "https://a.netatroniks.xyz", "http://diddifree.com", "https://diddifree.com:444",
    "https://-a.diddifree.com", "https://a_.diddifree.com", "https://%64iddifree.com",
    "http://127.0.0.1", "http://[::1]", "http://a.localhost", "http://localhost:0",
    "http://localhost:65536", "https://diddifree.com https://evil.test",
])
def test_rejected_origins(value: str) -> None:
    assert not is_allowed_origin(value, "test")


@pytest.mark.parametrize("port", ["", ":1", ":80", ":3000", ":65535"])
def test_localhost_only_in_nonproduction(port: str) -> None:
    value = "http://localhost" + port
    assert is_allowed_origin(value, "test")
    assert is_allowed_origin(value, "local")
    assert not is_allowed_origin(value, "production")


def test_normalization() -> None:
    assert normalize_origin("HTTPS://A.DIDDIFREE.COM:443") == "https://a.diddifree.com"
    assert normalize_origin("http://LOCALHOST:80") == "http://localhost"
