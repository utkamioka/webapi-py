from __future__ import annotations

import json
import os
from json import JSONDecodeError
from pathlib import Path

import click
import pytest
import toml
from _pytest.monkeypatch import MonkeyPatch

from webapi import main


@pytest.fixture
def tmp_dir(tmp_path: Path):
    cwd = Path.cwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(cwd)


def test_jsonify():
    obj = main.jsonify(None, None, '{"name": "john", "age": 20}')
    assert obj == {"name": "john", "age": 20}

    obj = main.jsonify(None, None, "[1, 2, 3, null]")
    assert obj == [1, 2, 3, None]


def test_jsonify__none():
    obj = main.jsonify(None, None, None)
    assert obj is None


def test_jsonify__illegal_json():
    with pytest.raises(click.BadParameter) as e:
        main.jsonify(None, None, "abc")
    assert e.value.__cause__.__class__ is JSONDecodeError


def test_jsonify__empty():
    with pytest.raises(click.BadParameter) as e:
        main.jsonify(None, None, "")
    assert e.value.__cause__.__class__ is JSONDecodeError


def test_jsonify__from_file(tmp_path: Path):
    path = tmp_path / "test.json"
    with path.open(mode="wt") as f:
        json.dump({"name": "john", "age": 20}, f)

    obj = main.jsonify(None, None, f"@{path}")
    assert obj == {"name": "john", "age": 20}


def test_jsonify__no_such_file(tmp_path: Path):
    with pytest.raises(click.BadParameter) as e:
        main.jsonify(None, None, f"@{tmp_path / 'no_such_file.json'}")
    assert e.value.__cause__.__class__ is FileNotFoundError


def test_read_file_if_starts_with_at(tmp_path: Path):
    assert main.read_file_if_starts_with_at("abc") == "abc"
    assert main.read_file_if_starts_with_at("") == ""
    assert main.read_file_if_starts_with_at(None) is None

    path = tmp_path / "input.txt"
    path.write_text("Hello, world")

    assert main.read_file_if_starts_with_at(f"@{path}") == "Hello, world"

    with pytest.raises(FileNotFoundError):
        main.read_file_if_starts_with_at("@no_such_file.txt")

    with pytest.raises(PermissionError):
        # Path("")をopen()をしようとした結果、PermissionErrorになる
        main.read_file_if_starts_with_at("@")


def test_validate_path_of_url():
    assert main.validate_path_of_url(None, None, "/") == "/"
    assert main.validate_path_of_url(None, None, "/foo") == "/foo"

    with pytest.raises(click.BadParameter):
        main.validate_path_of_url(None, None, "")

    with pytest.raises(click.BadParameter):
        # noinspection PyTypeChecker
        main.validate_path_of_url(None, None, None)


def test_parse_key_value_pair():
    obj = main.parse_key_value_pair(None, None, ["a:alpha", "b:bravo", "c:charlie"])
    assert obj == {
        "a": "alpha",
        "b": "bravo",
        "c": "charlie",
    }

    obj = main.parse_key_value_pair(None, None, ["a:alpha:bravo:charlie"])
    assert obj == {
        "a": "alpha:bravo:charlie",
    }

    obj = main.parse_key_value_pair(None, None, ["a:"])
    assert obj == {
        "a": "",
    }

    obj = main.parse_key_value_pair(None, None, [])
    assert obj == dict()


def test_parse_key_value_pair__invalid():
    with pytest.raises(ValueError):
        main.parse_key_value_pair(None, None, ["a"])


def test__path_to_session():
    assert main._path_to_session(appname="appname") == Path(".appname") / "session"


def test_restore_session__env(monkeypatch: MonkeyPatch):
    monkeypatch.setenv("APPNAME_HOST", "foo")
    monkeypatch.setenv("APPNAME_PORT", "65535")
    monkeypatch.setenv("APPNAME_AUTH_TOKEN", "bar")

    session = main.restore_session(appname="appname")

    assert session.host == "foo"
    assert session.port == 65535
    assert session.auth_token == "bar"


def test_restore_session__file(tmp_dir: Path):
    appname = "__appname__"

    assert tmp_dir == Path.cwd()

    path = Path(".") / f".{appname}" / "session"
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(mode="wt") as f:
        toml.dump({"host": "www.example.org", "port": 999, "auth_token": "*SECRET*"}, f)

    session = main.restore_session(appname=appname)

    assert session.host == "www.example.org"
    assert session.port == 999
    assert session.auth_token == "*SECRET*"


def test_restore_session__missing_both(tmp_dir: Path):
    with pytest.raises(click.ClickException):
        main.restore_session(appname="appname")


def test_restore_session__existing_both(monkeypatch: MonkeyPatch, tmp_dir: Path):
    appname = "appname"

    monkeypatch.setenv("APPNAME_HOST", "www1.example.org")
    monkeypatch.setenv("APPNAME_PORT", "1234")
    monkeypatch.setenv("APPNAME_AUTH_TOKEN", "*SECRET1*")

    path = tmp_dir / f".{appname}" / "session"
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(mode="wt") as f:
        toml.dump({"host": "www2.example.org", "port": 4321, "auth_token": "*SECRET2*"}, f)

    session = main.restore_session(appname="appname")

    # 環境変数とファイル、両方ある場合は、環境変数を優先適用
    assert session.host == "www1.example.org"
    assert session.port == 1234
    assert session.auth_token == "*SECRET1*"
