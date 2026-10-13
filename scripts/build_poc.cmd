@echo off
REM =====================================================================
REM  Phase-3-PoC: 32-Bit-Smoke-Link von Runtime + einer gelifteten TU.
REM  Ergebnis: build\juiced_poc.exe  (machine 0x014C = i386).
REM  Vollbau aller 120 TUs: siehe poc\CMakeLists.txt (rechenschwer).
REM =====================================================================
setlocal enableextensions
set "ROOT=%~dp0.."
cd /d "%ROOT%"
if not exist logs mkdir logs
if not exist build mkdir build

set "GCC=C:\msys64\mingw32\bin\gcc.exe"
set "INC=pcrecomp\runtime\recomp32"
set "GEN=juiced_lifted"
set "CFLAGS=-c -O0 -w -ffunction-sections -fdata-sections"

echo === [1/4] Runtime-Fix (weak-Symbol) ==============================
python scripts\patch_recomp_weak.py > logs\patch_recomp_weak.log 2>&1

echo === [2/4] Weak-Stubs erzeugen =====================================
python scripts\gen_weak_stubs.py %GEN%\recomp_funcs.h build\poc_stubs.c > logs\poc_stubs.log 2>&1

echo === [3/4] Kompilieren (i686-w64-mingw32, 32-bit) =================
"%GCC%" %CFLAGS% -I %INC% poc\main.c -o build\poc_main.o || goto :err
"%GCC%" %CFLAGS% -I %INC% -include %GEN%\recomp_funcs.h %GEN%\recomp_0000.c -o build\poc_recomp_0000.o || goto :err
"%GCC%" %CFLAGS% build\poc_stubs.c -o build\poc_stubs.o || goto :err

echo === [4/4] Linken =================================================
"%GCC%" build\poc_main.o build\poc_recomp_0000.o build\poc_stubs.o -Wl,--gc-sections -o build\juiced_poc.exe || goto :err

echo.
echo Fertig: build\juiced_poc.exe
endlocal
exit /b 0

:err
echo FEHLER (siehe logs\). 
endlocal
exit /b 1
