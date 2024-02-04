# webapi

Describe your project here.

## How to install python on windows

Visit [python.org](https://www.python.org/downloads/), or use `winget`.

```shell
winget install Python.Python.3.12
py -V  # => Python 3.12.0 
```

## How to activate(deactivate) venv on windows

* Create and move empty directory, and then...

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

## How to install

* with venv

```shell
# via HTTPS 
python -m pip install git+https://github.com/utkamioka/webapi-py.git
# via SSH
python -m pip install git+ssh://git@github.com/utkamioka/webapi-py.git
```

* without venv

```shell
py -m pip install --user git+https://github.com/utkamioka/webapi-py.git
py -m pip install --user git+ssh://git@github.com/utkamioka/webapi-py.git

# and adding following directory to PATH
py -m site --user-site  # => %AppData%\Python\PythonXY\site-packages 
```

## How to run


```shell
foo session -i 1.2.3.4 -p 9999 -U yamada -P asdf1234 
foo call GET /path/to/service/api --header foo:bar --header xxx:yyy --body '{}' 
```


# 注意


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
