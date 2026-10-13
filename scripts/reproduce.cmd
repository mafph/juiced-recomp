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
if not exist build mkdir build
set "JAVA_HOME=C:\Program Files\Java\jdk-24"

echo === [1/10] PE-Sektionen ============================================
python scripts\pe_sections.py Juiced.exe > logs\pe_sections.log 2>&1

echo === [2/10] Ghidra Import + Analyse (nur falls Projekt fehlt) =======
if not exist "ghidra_proj\JuicedDecomp.gpr" (
    call scripts\run_analyze.cmd
) else (
    echo Projekt vorhanden - uebersprungen. > logs\analyze_skip.log
)

echo === [3/10] Ghidra-Bereinigung (.securom + Nullsektion) =============
call scripts\stop_mcp.cmd            > logs\stop_mcp.log 2>&1
call scripts\run_cleanup.cmd

echo === [4/10] Sauberer C-Re-Export ====================================
call scripts\run_export.cmd

echo === [5/10] pcrecomp klonen + Abhaengigkeiten + Runtime-Fix =========
if not exist pcrecomp (
    git clone https://github.com/sp00nznet/pcrecomp > logs\pcrecomp_clone.log 2>&1
)
if exist pcrecomp\requirements.txt (
    python -m pip install -r pcrecomp\requirements.txt > logs\pip_install.log 2>&1
) else (
    python -m pip install capstone pefile lief unicorn cryptography > logs\pip_install.log 2>&1
)
git -C pcrecomp rev-parse HEAD > logs\pcrecomp_commit.log 2>&1
python scripts\patch_recomp_weak.py > logs\patch_recomp_weak.log 2>&1
python -m pip freeze > logs\pip_freeze.log 2>&1

echo === [6/10] PE-Flag-Patch (Nicht-Code-Sektionen) ====================
python scripts\patch_sections.py Juiced.exe build\Juiced.pcrecomp.exe .securom .data2 > logs\patch_sections.log 2>&1

echo === [7/10] PE-Analyse (pcrecomp, gepatchte Kopie) ==================
python pcrecomp\tools\pe\pe_analyze.py build\Juiced.pcrecomp.exe --json juiced_pe.json > logs\pe_analyze.log 2>&1

echo === [8/10] Disassemblierung (disasm32, gepatchte Kopie) ============
python pcrecomp\tools\disasm\disasm32.py build\Juiced.pcrecomp.exe --output juiced_functions.json --pe-json juiced_pe.json > logs\disasm32.log 2>&1

echo === [9/10] Lift (translator.py, gepatchte Kopie) ===================
if not exist juiced_lifted mkdir juiced_lifted
pushd pcrecomp
python -m tools ..\build\Juiced.pcrecomp.exe --all --output ..\juiced_lifted --split 500 > ..\logs\lift.log 2>&1
popd

echo === [10/10] PoC: Lifter-difftest ==================================
python pcrecomp\tools\lift\difftest.py > logs\difftest.log 2>&1

echo.
echo Fertig. Logs in logs\. Stand in docs\reproduktion.md abgleichen.
endlocal
