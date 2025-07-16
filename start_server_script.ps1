$env:PYTHONPATH = $PSScriptRoot
$serverScriptPath = "$PSScriptRoot/src/core/server.py"
Set-Location $PSScriptRoot
& .\.venv\Scripts\Activate.ps1
py $serverScriptPath

