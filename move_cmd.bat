@echo off

REM A script that lets you reposition the cmd prompt to a fixed position

REM Change the title to match the title of your Command Prompt window
set WINDOW_TITLE="C:\WINDOWS\system32\cmd.exe - py  main.py "

REM Use NirCmd to move the window to the second monitor
nircmd win move title %WINDOW_TITLE% -1400 -1

REM Pause to keep the window open
pause
