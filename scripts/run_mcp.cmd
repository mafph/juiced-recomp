@echo off
setlocal enableextensions
set "JAVA_HOME=C:\Program Files\Java\jdk-24"
set "GHIDRA_INSTALL_DIR=C:\Users\Marcos\Downloads\juicedDecomp\tools\ghidra_12.1.4_PUBLIC"
set "UV=C:\Users\Marcos\AppData\Local\Python\pythoncore-3.14-64\Scripts\uv.exe"
set "PROJDIR=C:\Users\Marcos\Downloads\juicedDecomp\ghidra_proj"
set "GPR=%PROJDIR%\JuicedDecomp.gpr"
set "LOG=C:\Users\Marcos\Downloads\juicedDecomp\mcp_server.log"
set "GUARDLOG=C:\Users\Marcos\Downloads\juicedDecomp\mcp_guard.log"

rem --- idempotenter Check: laeuft der Server schon auf Port 8000? ---
rem (locale-unabhaengig: kein "LISTENING"-Filter, da dt. Windows "ABHOEREN" ausgibt)
netstat -ano -p tcp | findstr /C:":8000 " >nul 2>&1
if not errorlevel 1 (
  rem eigener Logger, da der laufende Server die Datei %LOG% exklusiv offen haelt
  echo [%date% %time%] already running on port 8000, nothing to do>>"%GUARDLOG%"
  exit /b 0
)

if not exist "%UV%"  ( echo [%date% %time%] ERROR uv not found: %UV%>>"%LOG%" & exit /b 1 )
if not exist "%GPR%" ( echo [%date% %time%] ERROR project not found: %GPR%>>"%LOG%" & exit /b 1 )

rem --- verwaiste Ghidra-Locks entfernen (kein Server laeuft mehr) ---
del /q "%PROJDIR%\JuicedDecomp.lock" "%PROJDIR%\JuicedDecomp.lock~" 2>nul

echo [%date% %time%] starting pyghidra-mcp on http://127.0.0.1:8000/mcp>>"%LOG%"
"%UV%" tool run --python 3.12 pyghidra-mcp --transport streamable-http --host 127.0.0.1 --port 8000 --project-path "%GPR%" >>"%LOG%" 2>&1
echo [%date% %time%] server exited with %ERRORLEVEL%>>"%LOG%"
exit /b %ERRORLEVEL%
