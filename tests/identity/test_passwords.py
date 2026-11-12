import pytest
from argon2 import extract_parameters
from argon2.exceptions import InvalidHashError
from argon2.low_level import Type

from app.modules.identity.accounts import unavailable_reset
from app.modules.identity.passwords import Passwords
from app.shared.errors import EmailUnavailable


def test_hash_parameters_salts_and_verification() -> None:
    passwords = Passwords()
    encoded = passwords.hash("a sufficiently long password")
    parameters = extract_parameters(encoded)
    assert parameters.type == Type.ID
    assert (parameters.memory_cost, parameters.time_cost, parameters.parallelism) == (65536, 3, 1)
    assert (parameters.salt_len, parameters.hash_len) == (16, 32)
    assert passwords.hash("a sufficiently long password") != encoded
    assert passwords.verify(encoded, "a sufficiently long password")
    assert not passwords.verify(encoded, "wrong password")
    assert not passwords.verify(None, "wrong password")
    assert not passwords.needs_rehash(encoded)
    with pytest.raises(InvalidHashError):
        passwords.verify("corrupt", "wrong password")


def test_reset_fails_explicitly() -> None:
    with pytest.raises(EmailUnavailable) as error:
        unavailable_reset()
    assert error.value.status == 503
