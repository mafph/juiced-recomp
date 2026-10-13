@echo off
set "SRC=C:\Users\Marcos\Downloads\juicedDecomp\scripts\run_mcp_hidden.vbs"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
copy /Y "%SRC%" "%STARTUP%\juicedDecomp-mcp.vbs" >nul
if errorlevel 1 ( echo FEHLER beim Kopieren & exit /b 1 )
echo Autostart installiert: "%STARTUP%\juicedDecomp-mcp.vbs"
echo Der pyghidra-mcp-Server startet ab jetzt bei jeder Anmeldung versteckt.
