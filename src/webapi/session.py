from __future__ import annotations

import logging
import os
from operator import itemgetter
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
    def from_file(path: str | os.PathLike) -> AuthenticatedSession:
        return AuthenticatedSession.from_file(path)

    @staticmethod
    def from_env(prefix: str | None) -> AuthenticatedSession:
        return AuthenticatedSession.from_env(prefix)


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
    def from_file(cls, path: str | os.PathLike) -> AuthenticatedSession:
        path_to_session = Path(path).expanduser().resolve()

        with path_to_session.open(mode="r") as f:
            session = toml.load(f)
            return AuthenticatedSession(session["host"], session["port"], session["auth_token"])

    def write_to_file(self, path: str | os.PathLike, *, mkdir: bool = False) -> AuthenticatedSession:
        path_to_session = Path(path).expanduser().resolve()

        if mkdir:
            path_to_session.parent.mkdir(parents=True, exist_ok=True)

        with path_to_session.open(mode="w") as f:
            toml.dump(self._to_dict(), f)

        return self

    @classmethod
    def from_env(cls, prefix: str | None) -> AuthenticatedSession | None:
        prefix = prefix or ""

        names = [f"{prefix}{name}" for name in ("HOST", "PORT", "AUTH_TOKEN")]
        host, port, auth_token = itemgetter(*names)(os.environ)

        return AuthenticatedSession(host, int(port), auth_token)

    def print_to_env(self, prefix: str | None = None, file=None) -> AuthenticatedSession:
        prefix = prefix or ""

        # TODO: prefixに空白文字を含まないことを確認する

        for key, value in self._to_dict().items():
            print(f"export {prefix}{key.upper()}={value}", file=file)

        return self

    def _to_dict(self) -> dict[str, str | int]:
        return {"host": self.host, "port": self.port, "auth_token": self._auth_token}
