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

from webapi.credentials import Credentials, AuthenticatedCredentials


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


class TestCredentials:
    def test_constructor(self):
        credentials = Credentials("1.2.3.4", 1234, username="foo", password="bar")
        assert credentials.host == "1.2.3.4"
        assert credentials.port == 1234
        assert credentials.username == "foo"
        assert credentials.password == "bar"

    def test_str(self):
        credentials = Credentials("1.2.3.4", 1234, username="foo", password="bar")
        assert str(credentials) == "Credentials('1.2.3.4', 1234, 'foo', '****')"
        assert repr(credentials) == "Credentials('1.2.3.4', 1234, 'foo', '****')"


class TestAuthenticatedCredentials:
    def test_constructor(self):
        credentials = AuthenticatedCredentials("1.2.3.4", 1234, "SECRET_STRING")
        assert credentials.host == "1.2.3.4"
        assert credentials.port == 1234
        assert credentials.access_token == "SECRET_STRING"

    def test_str(self):
        credentials = AuthenticatedCredentials("1.2.3.4", 1234, "SECRET_STRING")
        # access_token(この場合は"SECRET_STRING")が表示されないこと
        assert str(credentials) == "AuthenticatedCredentials('1.2.3.4', 1234, '****')"
        assert repr(credentials) == "AuthenticatedCredentials('1.2.3.4', 1234, '****')"

    def test_from_file(self, tmp_path: Path, random_string: Callable):
        access_token = random_string(32)

        path = tmp_path / "__credentials__"

        with path.open(mode="wt") as f:
            print('host="www.example.org"', file=f)
            print("port=9999", file=f)
            print(f'access_token="{access_token}"', file=f)

        credentials = AuthenticatedCredentials.from_file(path)
        assert credentials.host == "www.example.org"
        assert credentials.port == 9999
        assert credentials.access_token == access_token

    def test_from_file__too_few_entries(self, tmp_path: Path):
        path = tmp_path / "__credentials__"

        with path.open(mode="wt") as f:
            # host is missing
            print("port=9999", file=f)
            print('access_token="SECRET"', file=f)

        with pytest.raises(KeyError):
            AuthenticatedCredentials.from_file(path)

        with path.open(mode="wt") as f:
            print('host="www.example.org"', file=f)
            # port is missing
            print('access_token="SECRET"', file=f)

        with pytest.raises(KeyError):
            AuthenticatedCredentials.from_file(path)

        with path.open(mode="wt") as f:
            print('host="www.example.org"', file=f)
            print("port=9999", file=f)
            # access_token is missing

        with pytest.raises(KeyError):
            AuthenticatedCredentials.from_file(path)

    def test_write_to_file(self, tmp_path: Path, random_string: Callable, random_int: Callable):
        host = random_string(10)
        port = random_int(0, 65535)
        access_token = random_string(32)
        credentials = AuthenticatedCredentials(host, port, access_token)

        path = tmp_path / "__credentials__"
        credentials.write_to_file(path)

        # TOML形式で書き込まれていること
        with path.open(mode="rt") as f:
            assert toml.load(f) == {"host": host, "port": port, "access_token": access_token}

    def test_write_to_file__mkdir(self, tmp_path: Path, random_string: Callable, random_int: Callable):
        host = random_string(10)
        port = random_int(0, 65535)
        access_token = random_string(32)
        credentials = AuthenticatedCredentials(host, port, access_token)

        path_under_subdir = tmp_path / "__subdir__" / "__credentials__"
        assert not path_under_subdir.parent.exists()

        with pytest.raises(FileNotFoundError):
            credentials.write_to_file(path_under_subdir)

        credentials.write_to_file(path_under_subdir, mkdir=True)
        assert path_under_subdir.parent.exists()
        assert path_under_subdir.exists()

    def test_from_env(self, monkeypatch: MonkeyPatch):
        monkeypatch.setenv("WEBAPI_HOST", "www.example.org")
        monkeypatch.setenv("WEBAPI_PORT", "9999")
        monkeypatch.setenv("WEBAPI_ACCESS_TOKEN", "SECRET_ACCESS_TOKEN")

        credentials = AuthenticatedCredentials.from_env(prefix="WEBAPI_")

        assert credentials.host == "www.example.org"
        assert credentials.port == 9999
        assert credentials.access_token == "SECRET_ACCESS_TOKEN"

    def test_from_env__port_not_int(self, monkeypatch: MonkeyPatch):
        monkeypatch.setenv("WEBAPI_HOST", "www.example.org")
        monkeypatch.setenv("WEBAPI_PORT", "123abc")
        monkeypatch.setenv("WEBAPI_ACCESS_TOKEN", "SECRET_ACCESS_TOKEN")

        with pytest.raises(ValueError):
            AuthenticatedCredentials.from_env(prefix="WEBAPI_")

    def test_print_to_env(self, capsys: CaptureFixture):
        credentials = AuthenticatedCredentials("www.example.org", 999, "*SECRET*")
        credentials.print_to_env(prefix="XXX_")

        captured = capsys.readouterr()

        assert (
            captured.out == "export XXX_HOST=www.example.org\nexport XXX_PORT=999\nexport XXX_ACCESS_TOKEN=*SECRET*\n"
        )
        assert captured.err == ""

    def test_print_to_env__empty_prefix(self, capsys: CaptureFixture):
        credentials = AuthenticatedCredentials("www.example.org", 123, "*SECRET*")
        credentials.print_to_env()

        captured = capsys.readouterr()

        assert captured.out == "export HOST=www.example.org\nexport PORT=123\nexport ACCESS_TOKEN=*SECRET*\n"
        assert captured.err == ""

    def test_print_to_env__to_stderr(self, capsys: CaptureFixture):
        credentials = AuthenticatedCredentials("www.example.org", 9999, "*SECRET*")
        credentials.print_to_env(file=sys.stderr)

        captured = capsys.readouterr()

        assert captured.out == ""
        assert captured.err == "export HOST=www.example.org\nexport PORT=9999\nexport ACCESS_TOKEN=*SECRET*\n"

    def test_purge(self, mocker: MockerFixture):
        credentials = AuthenticatedCredentials("", 0, "")
        mock = mocker.MagicMock()

        # on_purge()が指定されていなくてもエラーにはならないこと
        credentials.purge()

        # on_purge()の戻り値はCredentialsインスタンス自身であること
        assert credentials.on_purge(mock) is credentials

        mock.assert_not_called()

        credentials.purge()
        mock.assert_called_once()

        credentials.purge()
        mock.assert_has_calls([call(), call()])
