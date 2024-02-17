from __future__ import annotations

import copy
import json
import logging
from functools import partial, lru_cache
from typing import Callable

import click
import requests

from ._types import TypeJson
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

    def request(self, method: str, path: str, *, headers: dict[str, str] = None, body: TypeJson = None) -> _Request:
        return self._Request(self, method, path, headers, body)

    def apply_credential(self, headers: dict[str, str]) -> dict[str, str]:
        return self._credential_applier(self._session, headers)

    # def __call__(
    #     self,
    #     method: str,
    #     path: str,
    #     *,
    #     headers: dict[str, str] = None,
    #     body: TypeJson = None,
    # ) -> requests.Response:
    #     assert path.startswith("/")
    #
    #     headers = headers or dict()
    #
    #     url = f"https://{self.session.host}:{self.session.port}{path}"
    #
    #     headers = self._credential_applier(self.session, headers)
    #
    #     # cmd = []
    #     # cmd.extend(["curl", "-X", method.upper(), url])
    #     # for _key, _value in {"Content-Type": "application/json", **headers}.items():
    #     #     cmd.extend(["-H", repr(f"{_key}: {_value}")])
    #     # body and cmd.extend(["-d", repr(json.dumps(body))])
    #     # print(" ".join(cmd))
    #
    #     callers: dict[str, Callable] = {
    #         "GET": requests.get,
    #         "POST": partial(requests.post, json=body),
    #         "PUT": partial(requests.put, json=body),
    #         "PATCH": partial(requests.patch, json=body),
    #         "DELETE": requests.delete,
    #     }
    #
    #     method = method.upper()
    #     request_caller = callers.get(method, None)
    #     if request_caller is None:
    #         raise click.UsageError(f"Unsupported method {method!r}")
    #
    #     logger.info("%s %s", method, url)
    #
    #     response = request_caller(url, headers=headers, verify=False)
    #     logger.debug("response.status_code = %s(%s)", response.status_code, response.reason)
    #     logger.debug("response.text = %s", response.text)
    #
    #     if response.status_code != 200:
    #         raise HttpResponseError(response)
    #
    #     return response

    class _Request:
        def __init__(self, caller: Caller, method: str, path: str, headers: dict[str, str], data: TypeJson):
            assert path.startswith("/")

            self._caller = caller
            self._method = method.upper()
            self._path = path
            self._headers = copy.deepcopy(headers) if headers else dict()
            self._data = data

        @lru_cache(maxsize=1)
        def url(self) -> str:
            return f"https://{self._caller.session.host}:{self._caller.session.port}{self._path}"

        @lru_cache(maxsize=1)
        def headers(self) -> dict[str, str]:
            return self._caller.apply_credential(self._headers)

        def invoke(self) -> requests.Response:

            callers: dict[str, Callable] = {
                "GET": requests.get,
                "POST": partial(requests.post, json=self._data),
                "PUT": partial(requests.put, json=self._data),
                "PATCH": partial(requests.patch, json=self._data),
                "DELETE": requests.delete,
            }

            request_caller = callers.get(self._method, None)
            if request_caller is None:
                raise click.UsageError(f"Unsupported method {self._method!r}")

            logger.info("%s %s", self._method, self.url())

            response = request_caller(self.url(), headers=self.headers(), verify=False)
            logger.debug("response.status_code = %s(%s)", response.status_code, response.reason)
            logger.debug("response.text = %s", response.text)

            if response.status_code != 200:
                raise HttpResponseError(response)

            return response

        def similar_of_curl(self) -> str:
            cmdline = []

            cmdline.extend(["curl", "-X", self._method, self.url()])

            for _key, _value in self.headers().items():
                cmdline.extend(["-H", repr(f"{_key}: {_value}")])

            if self._data:
                cmdline.extend(["-H", repr("Content-Type: application/json")])
                cmdline.extend(["--data", repr(json.dumps(self._data))])

            return " ".join(cmdline)
