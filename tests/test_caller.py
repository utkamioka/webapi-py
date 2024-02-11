from __future__ import annotations

import re

import click
import requests_mock
import pytest
from pytest_mock import MockerFixture

from webapi.caller import Caller
from webapi.session import AuthenticatedSession


@pytest.fixture
def mock_request():
    with requests_mock.Mocker() as mock:
        yield mock


class TestCaller:
    def test_call(self, mock_request: requests_mock.Mocker):
        mock_request.get("https://www.example.com:9999/call", json={"method": "get"})
        mock_request.post("https://www.example.com:9999/call", json={"method": "post"})
        mock_request.put("https://www.example.com:9999/call", json={"method": "put"})
        mock_request.delete("https://www.example.com:9999/call", json={"method": "delete"})

        session = AuthenticatedSession("www.example.com", 9999, "**TOKEN**")
        caller = Caller(session, lambda _session, *args: args)

        assert caller("get", "/call").json() == {"method": "get"}
        assert caller("post", "/call").json() == {"method": "post"}
        assert caller("put", "/call").json() == {"method": "put"}
        assert caller("delete", "/call").json() == {"method": "delete"}

    def test_call__credential_applier(self, mock_request: requests_mock.Mocker, mocker: MockerFixture):
        mock_request.get("https://www.example.com:9999/any/path", json={"meth": "test_call__credential_applier"})

        session = AuthenticatedSession("www.example.com", 9999, "**TOKEN**")

        mock = mocker.MagicMock()
        mock.return_value = (dict(), dict())

        caller = Caller(session, mock)

        result = caller("get", "/any/path", headers={"Auth": "XXX"}, body={"name": "john"})

        # Caller()の第二引数に指定されたcredential_applierが、期待した引数で呼び出されていること
        mock.assert_called_once_with(
            session,  # args[0] = session
            {"Auth": "XXX"},  # args[1] = headers
            {"name": "john"},  # args[2] = body
        )

        assert result.json() == {"meth": "test_call__credential_applier"}

    def test_call__unknown_method(self, mock_request: requests_mock.Mocker):
        session = AuthenticatedSession("www.example.com", 9999, "**TOKEN**")
        caller = Caller(session, lambda _session, *args: args)

        with pytest.raises(click.UsageError) as e:
            caller("__xxx__", "/")

        match = re.match(r"^[Uu]nsupported method", e.value.args[0])
        assert match is not None
