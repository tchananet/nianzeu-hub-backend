import pytest
from pydantic import ValidationError

from app.modules.identity.schemas import CredentialsInput, EmailInput, ResetInput


def test_email_normalization() -> None:
    assert EmailInput(email=" User@EXAMPLE.COM ").email == "user@example.com"
    assert EmailInput(email="User@bücher.de").email == "user@xn--bcher-kva.de"


@pytest.mark.parametrize("email", ["é@example.com", "a", 123, True, "a\n@example.com"])
def test_invalid_email(email: object) -> None:
    with pytest.raises(ValidationError):
        EmailInput.model_validate({"email": email})


def test_password_preserved_and_role_forbidden() -> None:
    data = {"email": "a@example.com", "password": "  long password  "}
    assert CredentialsInput.model_validate(data).password == data["password"]
    with pytest.raises(ValidationError):
        CredentialsInput.model_validate({**data, "role": "talent"})


@pytest.mark.parametrize("password", ["short", "a" * 129, 123, True])
def test_password_bounds(password: object) -> None:
    with pytest.raises(ValidationError):
        CredentialsInput.model_validate({"email": "a@example.com", "password": password})


def test_reset_validation() -> None:
    ResetInput(token="a" * 43, password="a" * 12)
    for token in ["a" * 42, "a" * 129, "=" * 43]:
        with pytest.raises(ValidationError):
            ResetInput(token=token, password="a" * 12)
