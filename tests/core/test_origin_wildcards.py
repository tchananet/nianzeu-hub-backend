"""Wildcard entries such as `https://*.vercel.app`, used for preview deployments."""

import pytest

from app.core.origins import is_allowed_origin, usable_origin

WILDCARD = ("https://*.vercel.app",)


@pytest.mark.parametrize("value", [
    "https://nianzeu.vercel.app", "https://nianzeu-git-main-team.vercel.app",
    "https://a.b.vercel.app",
])
def test_a_wildcard_entry_trusts_its_subdomains(value: str) -> None:
    assert is_allowed_origin(value, "production", WILDCARD)


@pytest.mark.parametrize("value", [
    # The suffix itself is not a subdomain of itself, and a lookalike must not match.
    "https://vercel.app", "https://vercel.app.evil.test", "https://notvercel.app",
    "https://evilvercel.app",
    # Scheme and port still apply to a wildcard entry.
    "http://nianzeu.vercel.app", "https://nianzeu.vercel.app:444",
])
def test_a_wildcard_entry_does_not_trust_lookalikes(value: str) -> None:
    assert not is_allowed_origin(value, "production", WILDCARD)


def test_several_entries_are_all_honoured() -> None:
    allowed = ("https://app.example.com", "https://*.vercel.app")
    assert is_allowed_origin("https://app.example.com", "production", allowed)
    assert is_allowed_origin("https://preview.vercel.app", "production", allowed)
    assert not is_allowed_origin("https://other.test", "production", allowed)


@pytest.mark.parametrize("pattern", ["https://*.app", "https://*.", "https://*"])
def test_a_wildcard_over_a_whole_suffix_is_refused(pattern: str) -> None:
    # Trusting an entire TLD is never what someone means.
    with pytest.raises(ValueError):
        usable_origin(pattern, "production")


def test_a_wildcard_entry_is_accepted_and_normalised() -> None:
    assert usable_origin("HTTPS://*.VERCEL.APP", "production") == "https://*.vercel.app"
