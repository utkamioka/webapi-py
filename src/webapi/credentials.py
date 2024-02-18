from __future__ import annotations

import logging
import os
import stat
from abc import ABC
from operator import itemgetter
from pathlib import Path
from typing import Callable

import toml

logger = logging.getLogger(__name__)


class _Credentials(ABC):
    """認証情報の基底クラス。
    RestAPIの認証は接続先ごと（プロトコル＋ホスト名＋ポート番号）なので、
    基底クラスではホスト名とポート番号を保持する。
    プロトコルはHTTPS限定なので保持しない。
    """

    def __init__(self, host: str, port: int):
        self._host = host
        self._port = port

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port


class Credentials(_Credentials):
    """認証情報（未認証）。"""

    def __init__(self, host: str, port: int, username: str, password: str):
        super().__init__(host, port)
        self._username = username
        self._password = password

    def __repr__(self):
        return f"{self.__class__.__name__}({self._host!r}, {self._port!r}, {self._username!r}, '****')"

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return self._password

    def authenticate(self, authenticator: Callable[[Credentials], str]) -> AuthenticatedCredentials:
        """引数には認証情報からアクセストークンを生成する関数を指定する。"""
        access_token = authenticator(self)
        return AuthenticatedCredentials(self.host, self.port, access_token)

    @staticmethod
    def from_file(path: str | os.PathLike) -> AuthenticatedCredentials:
        return AuthenticatedCredentials.from_file(path)

    @staticmethod
    def from_env(prefix: str | None) -> AuthenticatedCredentials:
        return AuthenticatedCredentials.from_env(prefix)


class AuthenticatedCredentials(_Credentials):
    """認証情報（認証済み）。
    認証情報を含めてファイルへの保存と復元が出来る。

    TODO: 認証情報の暗号化も検討すること
    """

    def __init__(self, host: str, port: int, access_token: str):
        super().__init__(host, port)
        self._access_token = access_token
        self._on_purge = None

    def __repr__(self):
        return f"{self.__class__.__name__}({self._host!r}, {self._port!r}, '****')"

    @property
    def access_token(self) -> str:
        return self._access_token

    def on_purge(self, func: Callable) -> AuthenticatedCredentials:
        self._on_purge = func
        return self

    def purge(self) -> AuthenticatedCredentials:
        if callable(self._on_purge):
            self._on_purge()
        return self

    @classmethod
    def from_file(cls, path: str | os.PathLike) -> AuthenticatedCredentials:
        with Path(path).expanduser().resolve().open(mode="r") as f:
            obj = toml.load(f)
            return AuthenticatedCredentials(obj["host"], obj["port"], obj["access_token"])

    def write_to_file(self, path: str | os.PathLike, *, mkdir: bool = False) -> AuthenticatedCredentials:
        path = Path(path).expanduser().resolve()

        if mkdir:
            path.parent.mkdir(parents=True, exist_ok=True)

        with path.open(mode="w") as f:
            toml.dump(self._to_dict(), f)

        # ファイルオーナーのみ読み書き可能、なおWindowsでは機能しない
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

        return self

    @classmethod
    def from_env(cls, prefix: str | None) -> AuthenticatedCredentials | None:
        prefix = prefix or ""

        names = [f"{prefix}{name}" for name in ("HOST", "PORT", "ACCESS_TOKEN")]
        host, port, access_token = itemgetter(*names)(os.environ)

        return AuthenticatedCredentials(host, int(port), access_token)

    def print_to_env(self, prefix: str | None = None, file=None) -> AuthenticatedCredentials:
        prefix = prefix or ""

        # TODO: prefixに空白文字を含まないことを確認する

        for key, value in self._to_dict().items():
            print(f"export {prefix}{key.upper()}={value}", file=file)

        return self

    def _to_dict(self) -> dict[str, str | int]:
        return {"host": self.host, "port": self.port, "access_token": self._access_token}
