from __future__ import annotations

import random
import string
import sys
from pathlib import Path
from typing import Callable
from unittest.mock import call

import pytest
import toml
from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch
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


class TestAuthenticatedSession:
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

    def test_from_file(self, tmp_path: Path, random_string: Callable):
        path = tmp_path / "session"
        auth_token = random_string(32)
        with path.open(mode="wt") as f:
            print('host="www.example.org"', file=f)
            print("port=9999", file=f)
            print(f'auth_token="{auth_token}"', file=f)

        session = AuthenticatedSession.from_file(path)
        assert session.host == "www.example.org"
        assert session.port == 9999
        assert session.auth_token == auth_token

    def test_from_file__too_few_entries(self, tmp_path: Path):
        path = tmp_path / "session"

        with path.open(mode="wt") as f:
            # host is missing
            print("port=9999", file=f)
            print('auth_token="SECRET"', file=f)

        with pytest.raises(KeyError):
            AuthenticatedSession.from_file(path)

        with path.open(mode="wt") as f:
            print('host="www.example.org"', file=f)
            # port is missing
            print('auth_token="SECRET"', file=f)

        with pytest.raises(KeyError):
            AuthenticatedSession.from_file(path)

        with path.open(mode="wt") as f:
            print('host="www.example.org"', file=f)
            print("port=9999", file=f)
            # auth_token is missing

        with pytest.raises(KeyError):
            AuthenticatedSession.from_file(path)

    def test_write_to_file(self, tmp_path: Path, random_string: Callable, random_int: Callable):
        host = random_string(10)
        port = random_int(0, 65535)
        auth_token = random_string(32)
        session = AuthenticatedSession(host, port, auth_token)

        path = tmp_path / "session"
        session.write_to_file(path)

        # TOML形式で書き込まれていること
        with path.open(mode="rt") as f:
            assert toml.load(f) == {"host": host, "port": port, "auth_token": auth_token}

    def test_write_to_file__mkdir(self, tmp_path: Path, random_string: Callable, random_int: Callable):
        host = random_string(10)
        port = random_int(0, 65535)
        auth_token = random_string(32)
        session = AuthenticatedSession(host, port, auth_token)

        path_under_subdir = tmp_path / "__subdir__" / "session"
        assert not path_under_subdir.parent.exists()

        with pytest.raises(FileNotFoundError):
            session.write_to_file(path_under_subdir)

        session.write_to_file(path_under_subdir, mkdir=True)
        assert path_under_subdir.parent.exists()
        assert path_under_subdir.exists()

    def test_from_env(self, monkeypatch: MonkeyPatch):
        monkeypatch.setenv("WEBAPI_HOST", "www.example.org")
        monkeypatch.setenv("WEBAPI_PORT", "9999")
        monkeypatch.setenv("WEBAPI_AUTH_TOKEN", "SECRET_AUTH_TOKEN")

        session = AuthenticatedSession.from_env(prefix="WEBAPI_")

        assert session.host == "www.example.org"
        assert session.port == 9999
        assert session.auth_token == "SECRET_AUTH_TOKEN"

    def test_from_env__port_not_int(self, monkeypatch: MonkeyPatch):
        monkeypatch.setenv("WEBAPI_HOST", "www.example.org")
        monkeypatch.setenv("WEBAPI_PORT", "123abc")
        monkeypatch.setenv("WEBAPI_AUTH_TOKEN", "SECRET_AUTH_TOKEN")

        with pytest.raises(ValueError):
            AuthenticatedSession.from_env(prefix="WEBAPI_")

    def test_print_to_env(self, capsys: CaptureFixture):
        session = AuthenticatedSession("www.example.org", 999, "*SECRET*")
        session.print_to_env(prefix="XXX_")

        captured = capsys.readouterr()

        assert captured.out == "export XXX_HOST=www.example.org\nexport XXX_PORT=999\nexport XXX_AUTH_TOKEN=*SECRET*\n"
        assert captured.err == ""

    def test_print_to_env__empty_prefix(self, capsys: CaptureFixture):
        session = AuthenticatedSession("www.example.org", 123, "*SECRET*")
        session.print_to_env()

        captured = capsys.readouterr()

        assert captured.out == "export HOST=www.example.org\nexport PORT=123\nexport AUTH_TOKEN=*SECRET*\n"
        assert captured.err == ""

    def test_print_to_env__to_stderr(self, capsys: CaptureFixture):
        session = AuthenticatedSession("www.example.org", 9999, "*SECRET*")
        session.print_to_env(file=sys.stderr)

        captured = capsys.readouterr()

        assert captured.out == ""
        assert captured.err == "export HOST=www.example.org\nexport PORT=9999\nexport AUTH_TOKEN=*SECRET*\n"

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
