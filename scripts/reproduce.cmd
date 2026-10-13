@echo off
REM =====================================================================
REM  Reproduktion: Juiced.exe  x86 -> x86 Rekompilierung
REM  Siehe docs/reproduktion.md. Jeder Schritt schreibt nach logs\.
REM =====================================================================
setlocal enableextensions enabledelayedexpansion
set "ROOT=%~dp0.."
cd /d "%ROOT%"
if not exist logs mkdir logs
if not exist decompiled mkdir decompiled
set "JAVA_HOME=C:\Program Files\Java\jdk-24"

echo === [1/8] PE-Sektionen ============================================
python scripts\pe_sections.py Juiced.exe > logs\pe_sections.log 2>&1

echo === [2/8] Ghidra Import + Analyse (nur falls Projekt fehlt) ========
if not exist "ghidra_proj\JuicedDecomp.gpr" (
    call scripts\run_analyze.cmd
) else (
    echo Projekt vorhanden - uebersprungen. > logs\analyze_skip.log
)

echo === [3/8] Ghidra-Bereinigung (.securom + Nullsektion) ==============
call scripts\stop_mcp.cmd            > logs\stop_mcp.log 2>&1
call scripts\run_cleanup.cmd

echo === [4/8] Sauberer C-Re-Export ====================================
call scripts\run_export.cmd

echo === [5/8] pcrecomp klonen + Abhaengigkeiten =======================
if not exist pcrecomp (
    git clone https://github.com/sp00nznet/pcrecomp > logs\pcrecomp_clone.log 2>&1
)
if exist pcrecomp\requirements.txt (
    python -m pip install -r pcrecomp\requirements.txt > logs\pip_install.log 2>&1
) else (
    python -m pip install capstone pefile lief unicorn cryptography > logs\pip_install.log 2>&1
)
git -C pcrecomp rev-parse HEAD > logs\pcrecomp_commit.log 2>&1
python -m pip freeze > logs\pip_freeze.log 2>&1

echo === [6/8] PE-Analyse (pcrecomp) ====================================
python pcrecomp\tools\pe\pe_analyze.py Juiced.exe --json juiced_pe.json > logs\pe_analyze.log 2>&1

echo === [7/8] Disassemblierung (disasm32) ==============================
python pcrecomp\tools\disasm\disasm32.py Juiced.exe --output juiced.disasm > logs\disasm32.log 2>&1

echo === [8/8] Lift (translator.py) =====================================
if not exist juiced_lifted mkdir juiced_lifted
pushd pcrecomp
python -m tools ..\Juiced.exe --all --output ..\juiced_lifted\ > ..\logs\lift.log 2>&1
popd

echo.
echo Fertig. Logs in logs\. Stand in docs\reproduktion.md abgleichen.
endlocal
