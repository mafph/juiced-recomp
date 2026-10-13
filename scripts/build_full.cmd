@echo off
REM =====================================================================
REM  Phase 3: Vollbau - Runtime-Einstieg + ALLE gelifteten TUs (120 Dateien).
REM  Ergebnis: build\juiced_full.exe.
REM  Achtung: rechen-/speicherintensiv (Objekte ~600 MB, Link mit gc-sections).
REM  Weak-Stubs entfallen hier (alle sub_* sind in den TUs definiert).
REM =====================================================================
setlocal enableextensions enabledelayedexpansion
set "ROOT=%~dp0.."
cd /d "%ROOT%"
if not exist logs mkdir logs
if not exist build\full mkdir build\full

set "GCC=C:\msys64\mingw32\bin\gcc.exe"
set "INC=pcrecomp\runtime\recomp32"
set "GEN=juiced_lifted"
set "CFLAGS=-c -O0 -w -ffunction-sections -fdata-sections -Wno-error=implicit-function-declaration --param ggc-min-heapsize=32768 --param ggc-min-expand=10"

echo === [0/3] LAA-Flag fuer 32-Bit-cc1 (grosse TUs) ==================
python scripts\patch_cc1_laa.py > logs\patch_cc1_laa.log 2>&1

echo === [1/3] Runtime-Fix (weak-Symbol) ==============================
python scripts\patch_recomp_weak.py > logs\patch_recomp_weak.log 2>&1

echo === [1b/3] Undefinierte Sprungziel-Labels patchen ================
python scripts\patch_undefined_labels.py > logs\patch_undefined_labels.log 2>&1

echo === [2/3] Kompilieren (120 TUs) ==================================
set "OBJS="
set /a N=0
for %%F in ("%GEN%\recomp_*.c") do (
    if /i not "%%~nxF"=="recomp_dispatch.c" (
        set /a N+=1
        "%GCC%" %CFLAGS% -I %INC% -include %GEN%\recomp_funcs.h "%%~F" -o "build\full\%%~nF.o" || goto :err
        set "OBJS=!OBJS! build\full\%%~nF.o"
        echo   [!N!] %%~nxF
    )
)
"%GCC%" %CFLAGS% -I %INC% poc\main.c -o build\full\poc_main.o || goto :err

echo === [2b/3] Link-Stubs fuer undefinierte sub_* ====================
python scripts\gen_link_stubs.py build\full build\link_stubs.c "C:\msys64\mingw32\bin\nm.exe" || goto :err
"%GCC%" %CFLAGS% build\link_stubs.c -o build\full\link_stubs.o || goto :err

echo === [3/3] Linken (!N! TUs) =======================================
"%GCC%" build\full\poc_main.o build\full\link_stubs.o %OBJS% -Wl,--gc-sections -o build\juiced_full.exe || goto :err

echo.
echo Fertig: build\juiced_full.exe
endlocal
exit /b 0
:err
echo FEHLER (siehe logs\).
endlocal
exit /b 1
