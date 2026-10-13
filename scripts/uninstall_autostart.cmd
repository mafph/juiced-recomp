@echo off
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
del /q "%STARTUP%\juicedDecomp-mcp.vbs" 2>nul
echo Autostart entfernt.
