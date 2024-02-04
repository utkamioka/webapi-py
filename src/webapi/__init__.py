from importlib.metadata import version, PackageNotFoundError

try:
    # 指定したパッケージの定義（pyproject.toml）からバージョン番号を取得
    __version__ = version("webapi")
except PackageNotFoundError:
    __version__ = "unknown"
