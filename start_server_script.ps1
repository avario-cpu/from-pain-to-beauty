# Read the PROJECT_DIR_PATH location from .env
$PROJECT_DIR_PATH = (Get-Content .env | Where-Object { $_ -match '^PROJECT_DIR_PATH=' }) -replace '^PROJECT_DIR_PATH=', '' -replace '"', ''

$env:PYTHONPATH = $PROJECT_DIR_PATH
$serverScriptPath = "$PROJECT_DIR_PATH/src/core/server.py"

Set-Location $env:PYTHONPATH
& .\venv\Scripts\Activate.ps1
py $serverScriptPath

