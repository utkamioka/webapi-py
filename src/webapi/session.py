from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Callable

import toml

logger = logging.getLogger(__name__)


class Session:
    """認証情報を持たないセッション（未認証セッション）。"""

    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port

    def __repr__(self):
        return f"{self.__class__.__name__}({self._host!r}, {self._port!r})"

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    def authenticate(self, username: str, password: str, authenticator: Callable[[dict], str]) -> AuthenticatedSession:
        credentials = dict(host=self.host, port=self.port, username=username, password=password)

        auth_token = authenticator(credentials)

        return AuthenticatedSession(self.host, self.port, auth_token)

    @staticmethod
    def read_from(path: str | os.PathLike) -> AuthenticatedSession:
        return AuthenticatedSession.read_from(path)


class AuthenticatedSession(Session):
    """認証情報を持ったセッション（認証済みセッション）。
    認証情報を含めてファイルへの保存と復元が出来る。

    TODO: 認証情報の暗号化も検討すること
    """

    def __init__(self, host: str, port: int, auth_token: str):
        super().__init__(host, port)
        self._auth_token = auth_token
        self._on_purge = None

    def __repr__(self):
        return f"{self.__class__.__name__}({self._host!r}, {self._port!r}, '****')"

    @property
    def auth_token(self) -> str:
        return self._auth_token

    def on_purge(self, func: Callable) -> AuthenticatedSession:
        self._on_purge = func
        return self

    def purge(self) -> AuthenticatedSession:
        if callable(self._on_purge):
            self._on_purge()
        return self

    @classmethod
    def read_from(cls, path: str | os.PathLike):
        path_to_session = Path(path).expanduser().resolve()

        with path_to_session.open(mode="r") as f:
            session = toml.load(f)
            return AuthenticatedSession(session["host"], session["port"], session["auth_token"])

    def write_to(self, path: str | os.PathLike, *, mkdir: bool = False):
        path_to_session = Path(path).expanduser().resolve()

        if mkdir:
            path_to_session.parent.mkdir(parents=True, exist_ok=True)

        with path_to_session.open(mode="w") as f:
            toml.dump(self._to_dict(), f)

    def _to_dict(self) -> dict[str, str | int]:
        return {"host": self.host, "port": self.port, "auth_token": self._auth_token}
