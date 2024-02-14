# webapi

認証情報からアクセストークンを取得し、
アクセストークンによる認証付きWebAPIを呼び出すためのコマンドの雛形。

以下の２点は実際のサービスの仕様に合わせて実装して下さい。

* 認証情報からアクセストークンを取得
* リクエストにアクセストークンを適用

詳細は`src/webapi/dummy/auth.py`を参照して下さい。

## 使い方

### （１）認証してアクセストークンを取得

```shell
# 認証済みセッションへのアクセストークンをファイルに保存
webapi session --host www.example.org --user john --pass secret
webapi session --host www.example.org --user john
Password: ********
ls .webapi/session

# 認証済みセッションへのアクセストークンを環境変数に保存
eval `webapi session --host www.example.org --user john --pass secret --env`
printenv | grep WEBAPI
```

### （２）アクセストークンを使ってWebAPIを呼び出す

```shell
# アクセストークンは環境変数、またはファイルから取得され、RestAPIの呼び出しに自動適用
webapi call GET /any/request/path
webapi call POST /any/request/path --body '{"name": "john", "age": 21}'
```

## （ヒント）WindowsへのPythonインストール方法

Visit [python.org](https://www.python.org/downloads/), or use `winget`.

```shell
winget install Python.Python.3.12
py -V  # => Python 3.12.0 
```

## （ヒント）Windowsでvenvをactivate(deactivate)する方法

* 空のディレクトリへ移動してから、以下のコマンドを実行:

```shell
# on GitBash
py -m venv venv
source ./venv/Scripts/activate

deactivate
```

```shell
# on CMD.exe
py -m venv venv
.\venv\Scripts\activate.bat

deactivate
```

```shell
# on PowerShell
py -m venv venv
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\venv\Scripts\Activate.ps1

deactivate
```

## インストール方法

* venvへインストール（venvがactivateしてあること）

```shell
# via HTTPS 
python -m pip install git+https://github.com/utkamioka/webapi-py.git
# via SSH
python -m pip install git+ssh://git@github.com/utkamioka/webapi-py.git
```

* venvを使わずインストール（`--user`でユーザ固有環境にインストール）

```shell
py -m pip install --user git+https://github.com/utkamioka/webapi-py.git
py -m pip install --user git+ssh://git@github.com/utkamioka/webapi-py.git

# and adding following directory to PATH
py -m site --user-site  # => %AppData%\Python\PythonXY\site-packages 
```

## 実行方法


```shell
foo session -i 1.2.3.4 -p 9999 -U yamada -P asdf1234 
foo call GET /path/to/service/api --header foo:bar --header xxx:yyy --body '{}' 
```

## 注意


> [!NOTE]
> 
> [Git for windows](https://gitforwindows.org/)に含まれるGit BASHの場合、
> 文字`/`を`C:/Program Files/Git/`に置換してしまうため、
> `//`と記述する必要があります。
> ```shell
> rye run foo call GET /path/to/api  # BAD
> rye run foo call GET //path/to/api  # GOOD
> ```
> ```shell
> rye run foo call GET //path --body @~/input.json  # BAD
> rye run foo call GET //path --body @~//input.json  # GOOD
> ```


> [!NOTE]
> 
> PowerShellの場合`@`は特別な意味を持つため、
> シングルクォートで囲む必要があります。
> ```powershell
> rye run foo call GET /path --body @input.json  # BAD
> rye run foo call GET /path --body '@input.json'  # GOOD
> ```
