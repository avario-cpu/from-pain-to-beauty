REM script ued to run "start_server_script.ps1" as an executable from StreamDeck

@echo off
REM Use the directory where this batch file is located
set PSScriptPath="%~dp0start_server_script.ps1"
start powershell -NoProfile -ExecutionPolicy Bypass -File %PSScriptPath%
