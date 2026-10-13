@echo off
setlocal enableextensions
set "PROJDIR=C:\Users\Marcos\Downloads\juicedDecomp\ghidra_proj"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue; " ^
  "if ($p) { foreach ($x in $p) { Write-Host ('Stopping listener PID ' + $x.OwningProcess); Stop-Process -Id $x.OwningProcess -Force -ErrorAction SilentlyContinue } } " ^
  "Start-Sleep -Milliseconds 800; " ^
  "Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and ($_.Name -eq 'python.exe' -or $_.Name -eq 'uv.exe') -and $_.CommandLine -like '*pyghidra-mcp*' } | ForEach-Object { Write-Host ('Killing leftover PID ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

ping -n 3 127.0.0.1 >nul
del /q "%PROJDIR%\JuicedDecomp.lock" "%PROJDIR%\JuicedDecomp.lock~" 2>nul
echo pyghidra-mcp stopped and locks cleaned.
