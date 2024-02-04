from __future__ import annotations

import logging
from typing import Callable

import click

from webapi.session import AuthenticatedSession

logger = logging.getLogger(__name__)


class Caller:
    def __init__(self, session: AuthenticatedSession, credential_applier: Callable):
        click.echo(click.style(f"{self.__class__.__name__}()", fg="green"))
        self._session = session
        self._credential_applier = credential_applier

    @property
    def session(self) -> AuthenticatedSession:
        return self._session

    def __call__(self, method: str, path: str, *, headers: dict[str, str], body: str):
        click.echo(click.style(f"{self.__class__.__name__}.__call__()", fg="cyan"))
        headers, body = self._credential_applier(self.session, headers, body)
        click.echo(f"{method} https://{self.session.ipaddr}:{self.session.port}{path}")
        for key, value in headers.items():
            click.echo(f"\tHeader: {key} = {value}")
        click.echo(f"\tBody: {body}")
