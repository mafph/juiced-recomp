@echo off
REM Phase 3.1 - Runtime: echtes Image mappen + gelifteten Code ausfuehren.
REM Baut (falls noetig) build\juiced_run.exe und startet ihn gegen Juiced.exe.
REM Voraussetzung: build\full\*.o vorhanden (scripts\build_full.cmd einmal gelaufen).
setlocal
set "PATH=C:\msys64\mingw32\bin;%PATH%"

where ninja >nul 2>nul || (echo [FEHLER] ninja nicht im PATH & exit /b 1)
if not defined NINJA_J set NINJA_J=12

ninja -f build\build.ninja build/juiced_run.exe -j%NINJA_J% || exit /b 1
if errorlevel 1 exit /b 1

if "%~1"=="" (
  .\build\juiced_run.exe Juiced.exe
) else (
  .\build\juiced_run.exe "%~1"
)
endlocal
