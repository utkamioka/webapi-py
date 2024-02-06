from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Sequence

import click

from . import __version__
from webapi.caller import Caller, HttpResponseError
from webapi.dummy import auth
from webapi.session import Session

logger = logging.getLogger(__name__)


class CustomOrderGroup(click.Group):
    def list_commands(self, ctx: click.Context) -> list[str]:
        # Usageに表示されるサブコマンドの表示順序を制御するための仕掛け
        command_order = ["session", "call"]
        unlisted_commands = list(set(self.commands.keys()) - set(command_order))
        return command_order + unlisted_commands


def read_file_if_starts_with_at(_ctx: click.Context, _param: click.Argument, value: str) -> str:
    if value and value.startswith("@"):
        filename = value[1:]
        try:
            return Path(filename).expanduser().read_text()
        except FileNotFoundError:
            raise click.BadParameter(f"File {filename!r} not found.")
    return value


def validate_path_of_url(_ctx: click.Context, _param: click.Argument, value: str) -> str:
    if not value or not value.startswith("/"):
        raise click.BadParameter(f"{value}: must start with '/'")
    return value


def parse_key_value_pair(_ctx: click.Context, _param: click.Argument, values: Sequence[str]) -> dict[str, str]:
    result = {}
    for item in values:
        key, val = item.split(":", maxsplit=1)  # 最初の':'で分割
        result[key.strip()] = val.strip()
    return result


@click.group(cls=CustomOrderGroup, invoke_without_command=True)
@click.option("--version", "-V", is_flag=True, help="Show the version and exit.")
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Verbose mode. Can be used multiple times to increase verbosity.",
)
@click.pass_context
def cli(ctx: click.Context, version: bool, verbose: int) -> None:
    if version:
        click.echo(ctx.command_path + " " + __version__)
        ctx.exit()

    if verbose:
        if verbose == 1:
            logging.basicConfig(level=logging.INFO)
        elif verbose >= 2:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(levelname)s - %(funcName)s - %(message)s",
            )

    # サブコマンドが指定されていない場合はヘルプを表示
    # （--versionや--verboseのようなグローバルオプションを定義した場合、この処理が必要になる）
    if not ctx.invoked_subcommand:
        click.echo(ctx.get_help())


@cli.command(no_args_is_help=True)
@click.option("--host", "-h", help="Host name or IP address", required=True)
@click.option("--port", "-p", help="Port number", type=int, default=8080, show_default=True)
@click.option("--user", "-U", "username", help="Username", required=True)
@click.option("--pass", "-P", "password", help="Password", prompt=True, hide_input=True)
def session(host: str, port: int, username: str, password: str):
    (
        Session(host, port)
        .authenticate(username, password, authenticator=auth.authenticator)
        .write_to("~/.webapi/session", mkdir=True)
    )


@cli.command(no_args_is_help=True)
@click.option(
    "--header",
    "-H",
    "headers",
    multiple=True,
    help='Request headers (in "Host: example.com" format)',
    callback=parse_key_value_pair,
)
@click.option("--body", "-B", callback=read_file_if_starts_with_at, help="Request body")
@click.option("--pretty", "-p", is_flag=True, help="Pretty printing output")
@click.argument("method", type=click.Choice(["GET", "POST", "PUT", "DELETE"], case_sensitive=False))
@click.argument("path", callback=validate_path_of_url)
def call(method: str, path: str, headers: dict[str, str], body: str, pretty: bool):
    path_to_session = "~/.webapi/session"

    def remove_session_file():
        logger.debug("Removing session file %s", path_to_session)
        Path(path_to_session).expanduser().unlink(missing_ok=True)

    caller = Caller(
        Session.read_from(path_to_session).on_purge(remove_session_file),
        credential_applier=auth.credential_applier,
    )

    try:
        response = caller(method, path, headers=headers, body=body and json.loads(body))
        click.echo(json.dumps(response, indent=(2 if pretty else None)))
    except HttpResponseError as e:
        if e.args[0] == 401:
            # 401(Unauthorized)が発生したら認証情報を破棄
            caller.session.purge()

        click.echo("http status code = " + click.style(f"{e.args[0]}", fg="red", bold=True, blink=True))
        click.echo(e.args[1])


@cli.command()
def env():
    click.echo(click.style("Python path", fg="cyan") + ": " + sys.executable)
    click.echo(click.style("Python version", fg="cyan") + ": " + sys.version)


if __name__ == "__main__":
    cli()
