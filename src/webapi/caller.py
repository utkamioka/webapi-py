from __future__ import annotations

import logging
from functools import partial
from typing import Callable

import requests

from webapi.session import AuthenticatedSession

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

        method = method.upper()

        url = f"https://{self.session.host}:{self.session.port}{path}"
        logger.info("url = %s", url)

        headers, body = self._credential_applier(self.session, headers, body)
        logger.info("headers = %s", headers)
        logger.info("body = %s", body)

        if method == "GET":
            request_caller: Callable = requests.get
        elif method == "POST":
            request_caller: Callable = partial(requests.post, json=body)
        elif method == "PUT":
            request_caller: Callable = partial(requests.put, json=body)
        elif method == "DELETE":
            request_caller: Callable = requests.delete
        else:
            raise ValueError(f"Unsupported method {method!r}")

        logger.debug("http request caller = %s", request_caller)

        response = request_caller(url, headers=headers, verify=False)
        logger.debug("response.status_code = %s(%s)", response.status_code, response.reason)
        logger.debug("response.text = %s", response.text)

        if response.status_code != 200:
            raise HttpResponseError(response)

        return response
