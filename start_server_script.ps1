# This script sets the PYTHONPATH environment variable to the project directory
# then runs the server using the venv python.exe

# We assume that the PYTHONPATH and the project dir path are the same. (For now
# it seems to me to be the most flexible and practical way to go about this...)
$env:PYTHONPATH = "C:\Users\ville\MyMegaScript"
$serverScriptPath = "C:\Users\ville\MyMegaScript\src\core\server.py"

# Go to PYTHONPATH
Set-Location $env:PYTHONPATH

# Acivate venv
& .\venv\Scripts\Activate.ps1

# Run server.py
py $serverScriptPath



