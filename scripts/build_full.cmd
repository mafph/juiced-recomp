@echo off
REM =====================================================================
REM  Phase 3: Vollbau - Runtime-Einstieg + ALLE gelifteten TUs (120 Dateien).
REM  Ergebnis: build\juiced_full.exe.
REM
REM  Ablauf:  Patching/Stubs (sequenziell, klein)  ->  Ninja (parallel+inkrementell).
REM  Ninja nutzt ccache (falls installiert) + -jN.  NINJA_J=12 ist Default.
REM
REM  Inkremtenteller Rebuild (nach Aenderung an juiced_lifted\*.c):
REM      ninja -f build\build.ninja
REM  Einzelnes Objekt:
REM      ninja -f build\build.ninja build/full/recomp_0000.o
REM
REM  Hinweis: -w versteckt Warnungen (fuer den Rohling okay). Sobald der PoC
REM  laeuft, einmal OHNE -w bauen und die Warnungen nach logs\warnings.txt
REM  sammeln -- das sind die Prioritaeten beim Aufraeumen.
REM =====================================================================
setlocal enableextensions enabledelayedexpansion
set "ROOT=%~dp0.."
cd /d "%ROOT%"
REM gcc/cc1/ccache brauchen ihre DLLs (libgmp/libmpfr/...) aus mingw32\bin im PATH,
REM sonst stirbt cc1.exe still (kein Fehlertext, exit 1).
set "PATH=C:\msys64\mingw32\bin;%PATH%"
if not exist logs mkdir logs
if not exist build\full mkdir build\full

set "GCC=C:\msys64\mingw32\bin\gcc.exe"
set "NINJA=C:\msys64\mingw32\bin\ninja.exe"
if not defined NINJA_J set "NINJA_J=12"

echo === [0/3] LAA-Flag fuer 32-Bit-cc1 (grosse TUs) ==================
python scripts\patch_cc1_laa.py > logs\patch_cc1_laa.log 2>&1

echo === [1/3] Runtime-Fix (weak-Symbol) ==============================
python scripts\patch_recomp_weak.py > logs\patch_recomp_weak.log 2>&1

echo === [1b/3] Undefinierte Sprungziel-Labels patchen ================
python scripts\patch_undefined_labels.py > logs\patch_undefined_labels.log 2>&1

echo === [2/3] build.ninja erzeugen ==================================
python scripts\gen_build_ninja.py || goto :err

echo === [3/3] Kompilieren + Linken (Ninja -j%NINJA_J%) ===============
REM Link-Stubs werden als Ninja-Regel NACH dem Kompilieren erzeugt
REM (nm ueber build\full\*.o); die Reihenfolge steuert der build.ninja-Graph.
"%NINJA%" -f build\build.ninja -j %NINJA_J% > logs\build_full.log 2>&1
if errorlevel 1 ( type logs\build_full.log & goto :err )

echo.
echo Fertig: build\juiced_full.exe
endlocal
exit /b 0
:err
echo FEHLER (siehe logs\).
endlocal
exit /b 1
