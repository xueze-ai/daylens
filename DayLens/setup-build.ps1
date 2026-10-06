$ErrorActionPreference = 'Stop'
$uv = "$env:USERPROFILE\.local\bin\uv.exe"
if (!(Test-Path -LiteralPath $uv)) { throw 'uv not found' }
& $uv python install 3.11
& $uv venv --python 3.11 .venv
& $uv pip install --python .venv\Scripts\python.exe -r requirements.txt
