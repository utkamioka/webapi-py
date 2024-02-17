from __future__ import annotations

import contextlib
import json
import logging
import sys
from functools import partial
from importlib.metadata import distributions
from pathlib import Path
from typing import Sequence

import click
import mimeparse
import urllib3

from . import __version__
from ._types import TypeJson
from .caller import Caller, HttpResponseError
from .dummy import auth
from .session import Session, AuthenticatedSession

logger = logging.getLogger(__name__)


class CustomOrderGroup(click.Group):
    def list_commands(self, ctx: click.Context) -> list[str]:
        # Usageに表示されるサブコマンドの表示順序を制御するための仕掛け
        command_order = ["session", "call"]
        unlisted_commands = list(set(self.commands.keys()) - set(command_order))
        return command_order + unlisted_commands


def jsonify(_ctx, _param, value: str | None) -> TypeJson:
    try:
        text = read_file_if_starts_with_at(value)
    except OSError as e:
        raise click.BadParameter(f"{e.filename}: {e.args[-1]}") from e

    if text is not None:
        try:
            return json.loads(text)
        except Exception as e:
            raise click.BadParameter(f"{e!r}: text = {text!r}") from e

    return None


def read_file_if_starts_with_at(text: str | None) -> str | None:
    """文字列が'@'で始まる場合は、それをテキストファイルのファイル名と見なして、
    その内容を文字列で返す。
    そうでない場合は、文字列をそのまま帰す。
    """
    if text and text.startswith("@"):
        filename = text[1:]
        return Path(filename).expanduser().read_text()
    return text


def validate_path_of_url(_ctx, _param, value: str) -> str:
    """文字列が'/'で始まることを検証する。"""
    if not value or not value.startswith("/"):
        raise click.BadParameter(f"{value}: must start with '/'")
    return value


def parse_key_value_pair(_ctx, _param, values: Sequence[str]) -> dict[str, str]:
    """ "key:value"形式の文字列を格納した配列からdictに変換する。

    Examples:
        >>> parse_key_value_pair(["a:alpha", "b:bravo", "c:charlie"])
        {"a": "alpha", "b": "bravo", "c": "charlie"}
    """
    return dict(item.split(":", maxsplit=1) for item in values)


def _path_to_session(appname: str) -> Path:
    return Path(".") / ("." + appname) / "session"


def restore_session(*, appname: str) -> AuthenticatedSession:
    """環境変数またはファイルからセッションを復元する。"""
    with contextlib.suppress(KeyError):
        return Session.from_env(prefix=appname.upper() + "_")

    try:
        path_to_session = _path_to_session(appname)
        session_remover = partial(path_to_session.expanduser().absolute().unlink, missing_ok=True)

        return Session.from_file(path_to_session).on_purge(session_remover)
    except FileNotFoundError:
        raise click.ClickException(
            "No authenticated session. Please authenticate using the"
            " " + click.style("'session'", fg="red", bold=True) + " subcommand first."
        )


@click.group(cls=CustomOrderGroup, invoke_without_command=True)
@click.version_option(version=__version__)
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Verbose mode. Can be used multiple times to increase verbosity.",
)
@click.pass_context
def cli(ctx: click.Context, verbose: int) -> None:
    # suppress InsecureRequestWarning
    # See: https://urllib3.readthedocs.io/en/latest/advanced-usage.html#tls-warnings
    urllib3.disable_warnings()

    if verbose:
        if verbose == 1:
            logging.basicConfig(level=logging.INFO)
        elif verbose >= 2:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(levelname)s - %(funcName)s - %(message)s",
            )

    # サブコマンドが指定されていない場合はヘルプを表示
    # （--verboseのようなグローバルオプションを定義した場合、この処理が必要になる）
    if not ctx.invoked_subcommand:
        click.echo(ctx.get_help())


@cli.command(no_args_is_help=True)
@click.option("--host", "-h", help="Host name or IP address", required=True)
@click.option("--port", "-p", help="Port number", type=int, default=443, show_default=True)
@click.option("--user", "-U", "username", help="Username", required=True)
@click.option("--pass", "-P", "password", help="Password  [required, otherwise prompt]", prompt=True, hide_input=True)
@click.option("--env", "export_to_env", is_flag=True, help="Export session as environment variable to stdout")
@click.pass_context
def session(ctx: click.Context, host: str, port: int, username: str, password: str, export_to_env: bool) -> None:
    appname = ctx.parent.command_path

    authenticated_session = Session(host, port).authenticate(username, password, authenticator=auth.authenticator)

    if export_to_env:
        authenticated_session.print_to_env(prefix=appname.upper() + "_")
    else:
        authenticated_session.write_to_file(_path_to_session(appname))
        click.echo("Authentication was successful and the session was saved.")


@cli.command(no_args_is_help=True)
@click.option(
    "--header",
    "-H",
    "headers",
    multiple=True,
    help='Request headers (in "Host: example.com" format)',
    callback=parse_key_value_pair,
)
@click.option("--body", "-B", callback=jsonify, help="Request body")
@click.option("--curl", is_flag=True, help="Show curl command line")
@click.option("--show-header", is_flag=True, help="Show response header")
@click.option("--pretty", "-p", is_flag=True, help="Pretty printing output")
@click.argument("method", type=click.Choice(["GET", "POST", "PUT", "PATCH", "DELETE"], case_sensitive=False))
@click.argument("path", callback=validate_path_of_url)
@click.pass_context
def call(
    ctx: click.Context,
    method: str,
    path: str,
    headers: dict[str, str],
    body: TypeJson,
    curl: bool,
    show_header: bool,
    pretty: bool,
):
    appname = ctx.parent.command_path

    caller = Caller(restore_session(appname=appname), credential_applier=auth.credential_applier)
    request = caller.request(method, path, headers=headers, body=body)

    if curl:
        click.echo(request.similar_of_curl())
        sys.exit(0)

    try:
        response = request.invoke()

        if show_header:
            echo_stderr = partial(click.echo, err=True)

            echo_stderr(click.style(response.status_code, fg="blue") + " " + click.style(response.reason, fg="cyan"))
            for header in response.headers.items():
                echo_stderr(click.style(header[0], fg="cyan") + ": " + header[1])
            echo_stderr()

        _, subtype, _ = mimeparse.parse_mime_type(response.headers.get("Content-Type"))

        if subtype == "json":
            click.echo(json.dumps(response.json(), indent=(2 if pretty else None)))
        else:
            click.echo(response.text)
    except HttpResponseError as e:
        if e.status_code == 401:
            # 401(Unauthorized)が発生したら認証情報を破棄
            caller.session.purge()

        click.echo(click.style(str(e.status_code), fg="blue") + " " + click.style(e.reason, fg="cyan"), err=True)
        click.echo(e.text)


@cli.command()
def env():
    click.echo(click.style("Python path", fg="cyan") + ": " + sys.executable)
    click.echo(click.style("Python version", fg="cyan") + ": " + sys.version)

    dependencies = [f"{dist.metadata['Name']}=={dist.version}" for dist in distributions()]
    click.echo(click.style("Python dependencies", fg="cyan") + f": {dependencies}")


if __name__ == "__main__":
    cli()
