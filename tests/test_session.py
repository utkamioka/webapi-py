from __future__ import annotations

import random
import string
from pathlib import Path
from typing import Callable
from unittest.mock import call

import pytest
import toml
from pytest_mock import MockerFixture

from webapi.session import Session, AuthenticatedSession


@pytest.fixture
def random_string():
    def _random_string(length=10, seed=None):
        rng = random.Random(seed)
        characters = string.ascii_letters + string.digits
        return "".join(rng.choice(characters) for _ in range(length))

    return _random_string


@pytest.fixture
def random_int():
    def _random_int(min_value, max_value, seed=None):
        rng = random.Random(seed)
        return rng.randint(min_value, max_value)

    return _random_int


class TestSession:
    def test_constructor(self):
        session = Session("1.2.3.4", 1234)
        assert session.host == "1.2.3.4"
        assert session.port == 1234

    def test_str(self):
        session = Session("1.2.3.4", 1234)
        assert str(session) == "Session('1.2.3.4', 1234)"
        assert repr(session) == "Session('1.2.3.4', 1234)"


class TestAuthorization:
    def test_constructor(self):
        session = AuthenticatedSession("1.2.3.4", 1234, "SECRET_STRING")
        assert session.host == "1.2.3.4"
        assert session.port == 1234
        assert session.auth_token == "SECRET_STRING"

    def test_str(self):
        session = AuthenticatedSession("1.2.3.4", 1234, "SECRET_STRING")
        # auth_token(この場合は"SECRET_STRING")が表示されないこと
        assert str(session) == "AuthenticatedSession('1.2.3.4', 1234, '****')"
        assert repr(session) == "AuthenticatedSession('1.2.3.4', 1234, '****')"

    def test_read_from(self, tmp_path: Path, random_string: Callable):
        path = tmp_path / "session"
        auth_token = random_string(32)
        with path.open(mode="wt") as f:
            print('host="www.example.org"', file=f)
            print("port=9999", file=f)
            print(f'auth_token="{auth_token}"', file=f)

        session = AuthenticatedSession.read_from(path)
        assert session.host == "www.example.org"
        assert session.port == 9999
        assert session.auth_token == auth_token

    def test_read_from__too_few_entries(self, tmp_path: Path):
        path = tmp_path / "session"

        with path.open(mode="wt") as f:
            # host is missing
            print("port=9999", file=f)
            print('auth_token="SECRET"', file=f)

        with pytest.raises(KeyError):
            AuthenticatedSession.read_from(path)

        with path.open(mode="wt") as f:
            print('host="www.example.org"', file=f)
            # port is missing
            print('auth_token="SECRET"', file=f)

        with pytest.raises(KeyError):
            AuthenticatedSession.read_from(path)

        with path.open(mode="wt") as f:
            print('host="www.example.org"', file=f)
            print("port=9999", file=f)
            # auth_token is missing

        with pytest.raises(KeyError):
            AuthenticatedSession.read_from(path)

    def test_write_to(self, tmp_path: Path, random_string: Callable, random_int: Callable):
        host = random_string(10)
        port = random_int(0, 65535)
        auth_token = random_string(32)

        path = tmp_path / "session.toml"

        session = AuthenticatedSession(host, port, auth_token)
        session.write_to(path)

        # TOML形式で書き込まれていること
        with path.open(mode="rt") as f:
            assert toml.load(f) == {"host": host, "port": port, "auth_token": auth_token}

    def test_purge(self, mocker: MockerFixture):
        session = AuthenticatedSession("", 0, "")
        mock = mocker.MagicMock()

        # on_purge()が指定されていなくてもエラーにはならないこと
        session.purge()

        # on_purge()の戻り値はsession自身であること
        assert session.on_purge(mock) is session

        mock.assert_not_called()

        session.purge()
        mock.assert_called_once()

        session.purge()
        mock.assert_has_calls([call(), call()])
