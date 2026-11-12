"""Quota keys must identify a client without storing anything that identifies them.

data.md forbids a raw email or IP address in the quota table, and http.md requires the
key to be an HMAC of the normalised client under a server secret.
"""

import re

from app.core.primitives import ip_quota_key, quota_key

SECRET = "s" * 32
OTHER = "t" * 32
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def test_address_key_is_an_opaque_digest() -> None:
    address = "198.51.100.23"
    key = ip_quota_key(SECRET, address)
    assert HEX64.fullmatch(key)
    assert address not in key
    assert "198" not in key or len(key) == 64  # no substring of the address survives


def test_email_key_is_an_opaque_digest() -> None:
    email = "talent@example.com"
    key = quota_key(SECRET, email)
    assert HEX64.fullmatch(key)
    assert email not in key
    assert "talent" not in key


def test_the_server_secret_changes_the_key() -> None:
    # Without this, a leaked table would be reversible by brute-forcing addresses alone.
    assert ip_quota_key(SECRET, "198.51.100.23") != ip_quota_key(OTHER, "198.51.100.23")


def test_distinct_clients_get_distinct_keys() -> None:
    assert ip_quota_key(SECRET, "198.51.100.23") != ip_quota_key(SECRET, "198.51.100.24")


def test_mapped_addresses_cannot_split_one_client_into_two_quotas() -> None:
    # ::ffff:198.51.100.23 and 198.51.100.23 are the same client; if they produced two
    # keys, a client could double every per-IP limit just by changing representation.
    assert ip_quota_key(SECRET, "::ffff:198.51.100.23") == ip_quota_key(SECRET, "198.51.100.23")


def test_equivalent_ipv6_spellings_share_one_quota() -> None:
    assert ip_quota_key(SECRET, "2001:db8::1") == ip_quota_key(SECRET, "2001:0db8:0:0:0:0:0:1")
