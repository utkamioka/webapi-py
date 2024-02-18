from __future__ import annotations

import copy
import json
import logging
from functools import lru_cache
from typing import Callable

import requests

from ._types import TypeJson
from .credentials import AuthenticatedCredentials


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
    def __init__(self, credentials: AuthenticatedCredentials, credential_applier: Callable):
        """RestAPIを呼び出す。
        指定された認証情報をHTTPSリクエストに適用する。

        Args:
            credentials: 認証済み認証情報
            credential_applier: 認証情報をHTTPSリクエストに適用するための手続き（関数）
        """
        self._credentials = credentials
        self._credential_applier = credential_applier

    @property
    def credentials(self) -> AuthenticatedCredentials:
        return self._credentials

    def request(self, method: str, path: str, *, headers: dict[str, str] = None, body: TypeJson = None) -> _Request:
        """HTTPリクエストのメソッド・パス・ヘッダー・ボディを指定した
        リクエスト送信インスタンスを生成する。
        """
        return self._Request(self, method, path, headers, body)

    def apply_credential(self, headers: dict[str, str]) -> dict[str, str]:
        """認証情報をHTTPリクエストヘッダに適用する。"""
        return self._credential_applier(self._credentials, headers)

    class _Request:
        def __init__(self, caller: Caller, method: str, path: str, headers: dict[str, str], body: TypeJson):
            assert path.startswith("/")

            self._caller = caller
            self._method = method.upper()
            self._path = path
            self._headers = copy.deepcopy(headers) if headers else dict()
            self._body = body

        @lru_cache(maxsize=1)
        def url(self) -> str:
            """HTTPSリクエストの送信先。"""
            return f"https://{self._caller.credentials.host}:{self._caller.credentials.port}{self._path}"

        @lru_cache(maxsize=1)
        def headers(self) -> dict[str, str]:
            """認証情報を適用したHTTPヘッダを生成する。"""
            return self._caller.apply_credential(self._headers)

        def invoke(self) -> requests.Response:
            """HTTPSリクエストを発行しレスポンスを受信する。"""
            logger.info("%s %s", self._method, self.url())

            response = requests.request(self._method, self.url(), headers=self.headers(), json=self._body, verify=False)

            logger.debug("response.status_code = %s(%s)", response.status_code, response.reason)
            logger.debug("response.text = %s", response.text)

            if response.status_code != 200:
                raise HttpResponseError(response)

            return response

        def similar_of_curl(self) -> list[str]:
            """invoke()と同等の機能を有するcurlコマンド文字列を生成する。"""
            cmdline = []

            cmdline.extend(["curl", "--insecure", "-X", self._method, self.url()])

            for _key, _value in self.headers().items():
                cmdline.extend(["-H", repr(f"{_key}: {_value}")])

            if self._body:
                cmdline.extend(["-H", repr("Content-Type: application/json")])
                cmdline.extend(["--data", repr(json.dumps(self._body))])

            return cmdline
