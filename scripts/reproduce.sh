#!/usr/bin/env bash
# =====================================================================
#  Reproduktion: Juiced.exe  x86 -> x86 Rekompilierung
#  Siehe docs/reproduktion.md. Jeder Schritt schreibt nach logs/.
# =====================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p logs decompiled

echo "=== [1/8] PE-Sektionen ============================================"
python3 scripts/pe_sections.py Juiced.exe > logs/pe_sections.log 2>&1 || \
  python scripts/pe_sections.py Juiced.exe > logs/pe_sections.log 2>&1

echo "=== [2/8] Ghidra Import + Analyse (nur falls Projekt fehlt) ========"
if [ ! -e "ghidra_proj/JuicedDecomp.gpr" ]; then
    echo "Headless-Setup unter Linux: JAVA_HOME setzen, dann run_analyze analog."
    echo "Siehe docs/reproduktion.md." > logs/analyze_skip.log
else
    echo "Projekt vorhanden - uebersprungen." > logs/analyze_skip.log
fi

echo "=== [3/8] Ghidra-Bereinigung (MCP stoppen) ========================"
# Linux: MCP i.d.R. nicht aktiv; nur Headless-Cleanup
echo "(Headless-Cleanup siehe scripts/run_cleanup.cmd; Linux-Port noetig)"

echo "=== [4/8] Sauberer C-Re-Export ===================================="
echo "(run_export analog unter Linux: support/analyzeHeadless)" > logs/export_linux.log

echo "=== [5/8] pcrecomp klonen + Abhaengigkeiten ======================="
[ -d pcrecomp ] || git clone https://github.com/sp00nznet/pcrecomp > logs/pcrecomp_clone.log 2>&1
if [ -f pcrecomp/requirements.txt ]; then
    python3 -m pip install -r pcrecomp/requirements.txt > logs/pip_install.log 2>&1
else
    python3 -m pip install capstone pefile lief unicorn cryptography > logs/pip_install.log 2>&1
fi
git -C pcrecomp rev-parse HEAD > logs/pcrecomp_commit.log 2>&1
python3 -m pip freeze > logs/pip_freeze.log 2>&1

echo "=== [6/8] PE-Analyse (pcrecomp) ===================================="
python3 pcrecomp/tools/pe/pe_analyze.py Juiced.exe --json juiced_pe.json > logs/pe_analyze.log 2>&1

echo "=== [7/8] Disassemblierung (disasm32) =============================="
python3 pcrecomp/tools/disasm/disasm32.py Juiced.exe --output juiced.disasm > logs/disasm32.log 2>&1

echo "=== [8/8] Lift (translator.py) ====================================="
mkdir -p juiced_lifted
( cd pcrecomp && python3 -m tools ../Juiced.exe --all --output ../juiced_lifted/ ) > logs/lift.log 2>&1

echo
echo "Fertig. Logs in logs/. Stand in docs/reproduktion.md abgleichen."
