from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from argon2.low_level import Type

from app.core.primitives import new_secret


class Passwords:
    def __init__(self) -> None:
        self.hasher = PasswordHasher(
            time_cost=3, memory_cost=65536, parallelism=1,
            hash_len=32, salt_len=16, type=Type.ID,
        )
        self.dummy = self.hash(new_secret())

    def hash(self, password: str) -> str:
        return self.hasher.hash(password)

    def verify(self, encoded: str | None, password: str) -> bool:
        try:
            self.hasher.verify(encoded if encoded is not None else self.dummy, password)
        except VerifyMismatchError:
            return False
        return encoded is not None

    def needs_rehash(self, encoded: str) -> bool:
        return self.hasher.check_needs_rehash(encoded)
