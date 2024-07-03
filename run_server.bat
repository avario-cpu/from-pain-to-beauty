REM script to run "start_server_script.ps1" as an executable

@echo off
REM Set the path to the PowerShell script
set PSScriptPath="C:\Users\ville\MyMegaScript\start_server_script.ps1"

REM Execute the PowerShell script
start powershell -NoProfile -ExecutionPolicy Bypass -File %PSScriptPath%