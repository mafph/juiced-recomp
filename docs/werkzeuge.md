# Werkzeug-Referenz & Quirks

Übersicht aller Skripte unter `scripts/`, pcrecomp-Tools und bekannter Werkzeug-Einschränkungen.

## 1. Skripte (`scripts/`)

| Skript | Zweck | Wichtigste Flags / Nutzung |
|---|---|---|
| `reproduce.cmd` / `.sh` | End-to-End-Reproduktion (Schritte 0–3) | Vollständiger Durchlauf |
| `pe_sections.py` | PE-Sektionstabelle auslesen (Phase 1.1) | `python scripts/pe_sections.py <exe>` |
| `run_analyze.cmd` | Ghidra Headless: Import + Auto-Analyse | Nutzt `tools/ghidra_...` |
| `run_export.cmd` | Ghidra Headless: C-Export (`decompiled/`) | Nutzt Java-Export-Skript |
| `run_mcp.cmd` / `_hidden.vbs` | Startet pyghidra-mcp (Python 3.12 via uv) | Port 8000 |
| `stop_mcp.cmd` | Stoppt MCP-Server und gibt Ghidra-Lock frei | Vor Headless-Läufen nötig |
| `patch_sections.py` | Sektions-Flags patchen (`.securom`, `.data2`) | `python scripts/patch_sections.py <in> <out>` |
| `patch_recomp_weak.py` | pcrecomp weak-x87-Fix (E10) | Behebt g_st_i64-Kollision |
| `patch_undefined_labels.py` | Ergänzt fehlende Lift-Labels (E12) | Gegen `label used but not defined` |
| `patch_cc1_laa.py` | Setzt LAA in `cc1.exe`/`cc1plus.exe` (E12) | Gegen `cc1 out of memory` |
| `build_full.cmd` | Vollbau aller 120 TUs via Ninja | `scripts\build_full.cmd` |
| `build_poc.cmd` | Smoke-Link (eine TU, `recomp_0000.c`) | Testet Toolchain |
| `gen_build_ninja.py` | Erzeugt `build\build.ninja` | Inkrementell + ccache + Stubs |
| `gen_link_stubs.py` | Erzeugt weak-Stubs für ungelinkte `sub_*` | Läuft als Ninja-Regel nach Compile |
| `gen_weak_stubs.py` | Älterer weak-Stub-Generator für PoC | — |
| `iat_names.py` | Löst IAT-Slots / gebundene Adressen in Namen auf | `python scripts/iat_names.py 0x6CC1EC` |
| `run_image.cmd` | Baut `juiced_run.exe` und startet Runtime (3.1) | `scripts\run_image.cmd` |
| `find_leaf.py` | Sucht Blattfunktionen in `juiced_functions.json` | Für Difftest-Auswahl (3.4) |
| `difftest_fn.py` | Ein-Funktions-Difftest (geliftetes C vs. Unicorn) | `python scripts/difftest_fn.py <VA>` |
| `make_snapshot.ps1` | Portables Backup (Git-Bundle + Daten + Manifest) | `powershell -File scripts\make_snapshot.ps1` |

## 2. pcrecomp-Tools (`pcrecomp/tools/`)

- `pe/pe_analyze.py`: JSON-Export von Sektionen, Imports, Exports (`juiced_pe.json`).
- `disasm32/disasm32.py`: Rekursiver Descent vom Entry/Exports → `juiced_functions.json`.
- `lift/translator.py`: Massen-Lift nach C (`-m tools ... --all --split 500`).
- `lift/difftest.py`: Vergleicht 368 Instruktions-Corpusfälle gegen Unicorn.
- `disasm/callgraph.py`: Callgraph-Analyse (Callees, Callers, Hot, Leaves).

## 3. Bekannte Werkzeug-Quirks & Bugs

1. **`callgraph.py --bounds`**: Schlägt mit `ValueError: invalid literal for int(): 'entry'` fehl,
   weil der CSV-Header das Wort `entry` enthält.
2. **`translator.py --functions-json`**: Exportiert nur eine Zusammenfassung ohne Instruktionen;
   ist **nicht** als Lift-Eingabe verwendbar.
3. **`disasm32` Scan-Bereich**: Hat kein CLI-Argument zur Bereichsbeschränkung; das Ausschließen
   von `.securom` und `.data2` erfolgt ausschließlich über den PE-Section-Flag-Patch (`patch_sections.py`).
4. **`nm` Unterstrich**: i686-PE-Symbole tragen einen führenden Unterstrich (`_sub_…`).
5. **Kein `mingw32-make`**: MSYS2 liefert `make.exe`, aber kein `mingw32-make`. Build läuft über
   Ninja (`build.ninja`).
6. **`lld` defekt**: Das ucrt64-`lld`-Paket stürzt mit `0xC0000139` (`STATUS_ENTRYPOINT_NOT_FOUND`) ab;
   ein natives i686-`lld`-Paket existiert nicht. GNU `ld` dominiert den Link (~165 s).
7. **`native32` MSVC-only**: Die Bridge und der Callback-Trampolin nutzen MSVC-spezifisches Inline-Asm
   (`#error` unter MinGW).
8. **Deutsches Windows CLI**: `netstat` gibt `ABHÖREN` statt `LISTENING` aus (wichtig in `run_mcp.cmd`).
   `timeout`-Befehl schlägt bei umgeleitetem `stdin` fehl (wird durch `ping -n 3 127.0.0.1 >nul` ersetzt).
