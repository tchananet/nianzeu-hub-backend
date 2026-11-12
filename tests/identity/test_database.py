from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select

from app.modules.identity.models import Credential, LoginSession, User
from app.modules.identity.schemas import CredentialsInput
from app.shared.errors import AppError

pytestmark = pytest.mark.integration


def test_registration_login_rotation_logout(identity_db):
    service, factory, data = identity_db
    user = service.register(data)
    assert user.role == "talent"
    with pytest.raises(AppError) as error:
        service.register(data)
    assert error.value.status == 409
    login = service.login(data)
    assert service.authenticate(login.token).user.id == user.id
    with pytest.raises(AppError) as error:
        service.login(data, login.token)
    assert error.value.code == "CSRF_FAILED"
    rotated = service.login(data, login.token, login.identity.csrf_token)
    with pytest.raises(AppError):
        service.authenticate(login.token)
    service.logout(rotated.token, rotated.identity.csrf_token)
    with pytest.raises(AppError):
        service.authenticate(rotated.token)
    with factory() as db:
        encoded = db.scalar(select(Credential.password_hash).where(Credential.user_id == user.id))
        assert encoded.startswith("$argon2id$") and data.password not in encoded
        assert db.scalar(select(LoginSession.token_hash).where(
            LoginSession.id == rotated.identity.principal.session_id)) != rotated.token


def test_concurrent_duplicate_and_session_cap(identity_db):
    service, factory, data = identity_db

    def register():
        try:
            return service.register(data)
        except AppError as error:
            assert error.status == 409
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: register(), range(2)))
    assert sum(result is not None for result in results) == 1
    with ThreadPoolExecutor(max_workers=2) as pool:
        logins = list(pool.map(lambda _: service.login(data), range(6)))
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(LoginSession).where(
            LoginSession.user_id == logins[0].identity.user.id,
            LoginSession.revoked_at.is_(None))) == 5


def test_uniform_invalid_credentials_and_inactive(identity_db):
    service, factory, data = identity_db
    user = service.register(data)
    absent = CredentialsInput(email="missing-" + data.email, password=data.password)
    wrong = CredentialsInput(email=data.email, password="wrong long password")
    for attempt in [absent, wrong]:
        with pytest.raises(AppError) as error:
            service.login(attempt)
        assert (error.value.status, error.value.code) == (401, "INVALID_CREDENTIALS")
    token = service.login(data).token
    with factory.begin() as db:
        db.get(User, user.id).is_active = False
    for call in [lambda: service.login(data), lambda: service.authenticate(token)]:
        with pytest.raises(AppError) as error:
            call()
        assert error.value.status == 401
