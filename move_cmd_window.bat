@echo off

REM Reposition the terminal to somwhere fucking decent when in the middle of game :D

REM Change the title to match the title of your Command Prompt window
set WINDOW_TITLE="C:\WINDOWS\system32\cmd.exe - py  main.py "

REM Use NirCmd to move and resize the window to the left and smaller (params: Xmove, Ymove, Xresize, Yresize)
nircmd win move title %WINDOW_TITLE% -470 700 -800 -400

REM Use NirCmd to set the size of the window

REM Pause to keep the window open
