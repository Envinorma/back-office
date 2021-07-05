from dataclasses import dataclass

from flask_login import current_user

from back_office.config import LOGIN_PASSWORD, LOGIN_USERNAME


@dataclass
class User:
    username: str
    password: str
    active: bool = True
    authenticated: bool = True
    anonymous: bool = False

    def get_id(self) -> str:
        return self.username

    @property
    def is_active(self):
        return self.active

    @property
    def is_authenticated(self):
        return self.authenticated

    @property
    def is_anonymous(self):
        return self.anonymous


UNIQUE_USER = User(LOGIN_USERNAME, LOGIN_PASSWORD)
ANONYMOUS_USER = User('anonymous', '', False, False, True)


def get_current_user() -> User:
    return current_user or ANONYMOUS_USER  # type: ignore
