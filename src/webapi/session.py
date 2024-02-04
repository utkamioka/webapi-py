from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Callable

import click
import toml

logger = logging.getLogger(__name__)


class Session:
    """認証情報を持たないセッション（未認証セッション）。"""

    def __init__(self, ipaddr: str, port: int):
        click.echo(click.style(f"{self.__class__.__name__}({ipaddr!r}, {port!r})", fg="green"))
        self._ipaddr = ipaddr
        self._port = port

    def __repr__(self):
        return f"{self.__class__.__name__}({self._ipaddr!r}, {self._port!r})"

    @property
    def ipaddr(self):
        return self._ipaddr

    @property
    def port(self):
        return self._port

    def authenticate(self, username: str, password: str, authenticator: Callable[[dict], str]) -> AuthenticatedSession:
        click.echo(click.style(f"{self}.authenticate({username=!r}, {password=!r})", fg="cyan"))

        credentials = dict(ipaddress=self.ipaddr, port=self.port, username=username, password=password)
        auth_token = authenticator(credentials)

        return AuthenticatedSession(self.ipaddr, self.port, auth_token)

    @staticmethod
    def read_from(path: str | os.PathLike) -> AuthenticatedSession:
        return AuthenticatedSession.read_from(path)


class AuthenticatedSession(Session):
    """認証情報を持ったセッション（認証済みセッション）。
    認証情報を含めてファイルへの保存と復元が出来る。

    TODO: 認証情報の暗号化も検討すること
    """

    def __init__(self, ipaddr: str, port: int, auth_token: str):
        super().__init__(ipaddr, port)
        click.echo(
            click.style(
                f"{self.__class__.__name__}({ipaddr!r}, {port!r}, {auth_token!r})",
                fg="green",
            )
        )
        self._auth_token = auth_token

    def __repr__(self):
        return f"{self.__class__.__name__}({self._ipaddr!r}, {self._port!r}, '****')"

    @property
    def auth_token(self) -> str:
        return self._auth_token

    @classmethod
    def read_from(cls, path: str | os.PathLike):
        click.echo(click.style(f"{cls.__name__}.read_from({path=})", fg="cyan"))
        with Path(path).expanduser().open(mode="r") as f:
            logger.debug("Reading session from %s", path)
            session = toml.load(f)
            return AuthenticatedSession(session["ipaddr"], session["port"], session["auth_token"])

    def write_to(self, path: str | os.PathLike):
        click.echo(click.style(f"{self.__class__.__name__}.write_into({path=})", fg="cyan"))
        with Path(path).expanduser().open(mode="w") as f:
            logger.debug("Writing session into %s", path)
            toml.dump(self._to_dict(), f)

    def _to_dict(self) -> dict[str, str | int]:
        return dict(ipaddr=self.ipaddr, port=self.port, auth_token=self._auth_token)
