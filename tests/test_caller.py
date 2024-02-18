from __future__ import annotations

import requests_mock
import pytest
from pytest_mock import MockerFixture

from webapi.caller import Caller
from webapi.credentials import AuthenticatedCredentials


@pytest.fixture
def mock_request():
    with requests_mock.Mocker() as mock:
        yield mock


class TestCaller:
    def test_request_invoke(self, mock_request: requests_mock.Mocker):
        mock_request.get("https://www.example.com:9999/call", json={"method": "get"})
        mock_request.post("https://www.example.com:9999/call", json={"method": "post"})
        mock_request.put("https://www.example.com:9999/call", json={"method": "put"})
        mock_request.patch("https://www.example.com:9999/call", json={"method": "patch"})
        mock_request.delete("https://www.example.com:9999/call", json={"method": "delete"})

        credentials = AuthenticatedCredentials("www.example.com", 9999, "**TOKEN**")
        caller = Caller(credentials, credential_applier=(lambda _credentials, headers: headers))

        assert caller.request("get", "/call").invoke().json() == {"method": "get"}
        assert caller.request("post", "/call").invoke().json() == {"method": "post"}
        assert caller.request("put", "/call").invoke().json() == {"method": "put"}
        assert caller.request("patch", "/call").invoke().json() == {"method": "patch"}
        assert caller.request("delete", "/call").invoke().json() == {"method": "delete"}

    def test_request_invoke_twice(self, mock_request: requests_mock.Mocker):
        """一つのCallerインスタンスで二回のリクエストを発行するケース。"""
        mock_request.get("https://www.example.com:9999/call1", json={"method": "get1"})
        mock_request.get("https://www.example.com:9999/call2", json={"method": "get2"})

        credentials = AuthenticatedCredentials("www.example.com", 9999, "**TOKEN**")
        caller = Caller(credentials, credential_applier=(lambda _credentials, headers: headers))

        assert caller.request("get", "/call1").invoke().json() == {"method": "get1"}
        assert caller.request("get", "/call2").invoke().json() == {"method": "get2"}

    def test_call__credential_applier(self, mock_request: requests_mock.Mocker, mocker: MockerFixture):
        mock_request.get("https://www.example.com:9999/any/path", json={})

        credentials = AuthenticatedCredentials("www.example.com", 9999, "**TOKEN**")

        mock_credential_applier = mocker.MagicMock()
        mock_credential_applier.return_value = {"X-Auth-Token": "**SECRET**"}  # 実際にHTTPリクエストに適用されるヘッダ

        caller = Caller(credentials, credential_applier=mock_credential_applier)
        request = caller.request("get", "/any/path", headers={"X-Request": "X-Request-value"})

        result = request.invoke()

        # Caller()の第二引数credential_applierが、期待した引数で呼び出されていること
        mock_credential_applier.assert_called_once_with(
            credentials,  # args[0] = instance of AuthenticatedCredentials
            {"X-Request": "X-Request-value"},  # args[1] = headers
        )

        # Caller()の第二引数credential_applierで生成したヘッダが、HTTPリクエストに適用されていること
        assert ("X-Auth-token", "**SECRET**") in result.request.headers.items()

    def test_similar_of_curl(self):
        credentials = AuthenticatedCredentials("www.example.com", 9999, access_token="**TOKEN**")
        caller = Caller(credentials, credential_applier=(lambda _credentials, headers: headers))

        request = caller.request("get", "/get")
        assert request.similar_of_curl() == ["curl", "--insecure", "-X", "GET", "https://www.example.com:9999/get"]

        request = caller.request("post", "/post", headers={"Foo": "bar"}, body={"name": "alice", "age": 19})
        assert request.similar_of_curl() == [
            "curl",
            "--insecure",
            "-X",
            "POST",
            "https://www.example.com:9999/post",
            "-H",
            "'Foo: bar'",
            "-H",
            "'Content-Type: application/json'",
            "--data",
            '\'{"name": "alice", "age": 19}\'',
        ]
