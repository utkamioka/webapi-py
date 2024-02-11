from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path

import click
import pytest

from webapi import main


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
