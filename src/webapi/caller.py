from __future__ import annotations

import logging
from functools import partial
from typing import Callable

import click
import requests

from .session import AuthenticatedSession

logger = logging.getLogger(__name__)


class HttpResponseError(Exception):
    def __init__(self, response: requests.Response):
        self.response = response

    @property
    def status_code(self) -> int:
        return self.response.status_code

    @property
    def reason(self) -> str:
        return self.response.reason

    @property
    def text(self) -> str:
        return self.response.text


class Caller:
    def __init__(self, session: AuthenticatedSession, credential_applier: Callable):
        self._session = session
        self._credential_applier = credential_applier

    @property
    def session(self) -> AuthenticatedSession:
        return self._session

    def __call__(self, method: str, path: str, *, headers: dict[str, str], body: dict) -> requests.Response:
        assert path.startswith("/")

        url = f"https://{self.session.host}:{self.session.port}{path}"

        headers, body = self._credential_applier(self.session, headers, body)

        callers = {
            "GET": requests.get,
            "POST": partial(requests.post, json=body),
            "PUT": partial(requests.put, json=body),
            "DELETE": requests.delete,
        }

        method = method.upper()
        request_caller = callers.get(method, None)
        if request_caller is None:
            raise click.UsageError(f"Unsupported method {method!r}")

        logger.info("%s %s", method, url)

        response = request_caller(url, headers=headers, verify=False)
        logger.debug("response.status_code = %s(%s)", response.status_code, response.reason)
        logger.debug("response.text = %s", response.text)

        if response.status_code != 200:
            raise HttpResponseError(response)

        return response
