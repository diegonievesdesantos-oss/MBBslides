@echo off
rem Windows (cmd.exe) wrapper: run the engine from a checkout without installing it.
set "HERE=%~dp0.."
set "PYTHONPATH=%HERE%\src;%PYTHONPATH%"
set "PYTHONUTF8=1"
where py >nul 2>nul && (py -3 -m cpe %*) || (python -m cpe %*)
