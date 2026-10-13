# Reproduktion — Schritt für Schritt

Format je Schritt: **Ziel · Voraussetzungen · Befehl · Erwartet · Tatsächlich · Abweichung.**

> Automatisierung: `scripts\reproduce.cmd` (Windows) bzw. `bash scripts/reproduce.sh`
> (Linux). Alle Befehle schreiben nach `logs/`.

## Voraussetzungen (einmalig)

| | |
|---|---|
| Python | 3.10+ (hier 3.14.2) |
| Ghidra | 12.1.4 unter `tools/ghidra_12.1.4_PUBLIC` |
| Java | JDK 21+ (hier 24), `JAVA_HOME` gesetzt |
| Ziel-Binary | `Juiced.exe` im Projektroot (SHA256 siehe `docs/umgebung.md`) |
| pcrecomp | wird von `reproduce` geklont |

---

## Phase 0 — Grundlagen

Siehe `docs/README.md`, `docs/architektur.md`, `docs/entscheidungen.md`.
Kein ausführbarer Schritt.

## Phase 1 — Ghidra-Bereinigung

Ziel: Müll aus `.securom` und der Nullsektion entfernen, Sektionen als Daten markieren.
**Hinweis:** dient Verständnis/Referenz; pcrecomp-Input bleibt unberührt (siehe E5).

### 1.1 Sektionsgrenzen verifizieren

- **Befehl:** `python scripts/pe_sections.py Juiced.exe`
- **Log:** `logs/pe_sections.log`
- **Erwartet:** 11 Sektionen; `.text` 0x401000, `.securom` 0xF93000, unbenannte 17-MB-Sektion.
- **Tatsächlich:** 11 Sektionen, ImageBase 0x400000. `.text`(1) 0x401000–0x6CC000,
  `.text`(2) 0x7AB000–0xCCE000, `.data`(2) 0xCDB000–0xF93000 (**EXECUTE**),
  `.securom` 0xF93000–**0x1030000**, unbenannt 0x1030000–0x2142000, `.SCY` 0x2142000.
- **Abweichung:** Auftrag nannte `.securom`-Ende 0x102A000 → korrekt ist **0x1030000**.
  Zusätzlich: `.data2` trägt das EXECUTE-Flag.

### 1.2 Stichproben aus `.text` prüfen

- **Befehl (MCP):** `decompile_function`/`disassemble`/`read_bytes` auf `0x5CD316` und `0x401000`.
- **Erwartet:** valider MSVC-Prolog, Decompiler passt zu Bytes.
- **Tatsächlich:** `0x5CD316` = CRT-Startup (`PUSH 0x60`, `__heap_init`, `__mtinit`,
  `GetStartupInfoA`, `FUN_005a5790`). `0x401000` Bytes `8b0d50107600…`
  = `mov ecx,[0x761050]` — deckt sich mit Decompiler. Sauber.
- **Abweichung:** keine.

### 1.3 `.data2` klassifizieren

- **Befehl (MCP):** `read_bytes` (mehrere Punkte) + `list_xrefs`.
- **Erwartet:** Entscheidung Daten vs. Code.
- **Tatsächlich:** 0xCDB000/0xD00000/0xD80000/0xF50000 = Nullen; **0xE80000 = echte
  Code-Bytes** (`e9…`, `c7 85…`, `8b 4d 0c`, `83 7d f4 00`); 0xE00000 wird von
  `FUN_0068a406`/`FUN_0068afb3` als **Daten** referenziert; 0xF90000 = Datentabellen.
- **Ergebnis:** `.data2` **behalten** (nicht löschen).
- **Abweichung:** Ghidras 1.726 Funktionen in `.data2` sind überwiegend Falsch-Positive
  (EXECUTE-Flag), aber die Sektion enthält echten Inhalt → behalten.

### 1.4 Müll entfernen (`.securom` + Nullsektion)

- **Befehl:** `scripts\run_cleanup.cmd` (Ghidra-Headless, `CleanupSections.java`)
  - Voraussetzung: MCP-Server gestoppt (`scripts\stop_mcp.cmd`), da er das Projekt sperrt.
- **Log:** `logs/cleanup.log`
- **Erwartet:** Funktionen in `.securom` + unbenannter Sektion entfernt, als Daten markiert.
- **Tatsächlich:** `.securom` (0xF93000–0x102FFFF): **322** Funktionen entfernt;
  unbenannt (0x1030000–0x2141FFF): **5** entfernt. Ghidra-Zählung 13968 → 13332
  (Netto −636, d. h. über die 327 expliziten hinaus entfernte `clearListing`
  überlappende Restfunktionen). `DONE_EXIT_0`.
- **Abweichung:** pyghidra-mcp 0.2.7 hat kein `clear` → Headless-Skript statt MCP.

### 1.5 Bereinigung verifizieren

- **Befehl:** Auswertung von `decompiled/functions.csv` (nach 1.6).
- **Erwartet:** keine Funktion in 0xF93000–0x2142000.
- **Tatsächlich:** Gesamt **13128** Funktionen; davon **0** in `.securom`+Nullsektion;
  **1726** in `.data2` (bewusst behalten, siehe E4); 6 Dekompilier-Fehler.
- **Abweichung:** Auftrags-Schätzung „~11.700–11.900" galt nur bei Mitlöschung der
  `.data2`-Funktionen; da `.data2` behalten wird, bleiben 13128.

### 1.6 Sauberer Re-Export

- **Befehl:** `scripts\run_export.cmd`
- **Log:** `logs/export.log`
- **Erwartet:** `decompiled/all_functions.c` ohne Müll.
- **Tatsächlich:** `DONE_EXIT_0`, 13122/13128 Funktionen dekompiliert,
  `all_functions.c` 19.504.879 Bytes, `functions.csv` 522.944 Bytes (17:22 Uhr).

---

## Phase 2 — pcrecomp (x86 → x86)

### 2.1 pcrecomp beschaffen

- **Befehl:** `git clone <pcrecomp>` + Deps in `.venv` installieren.
- **Log:** `logs/pcrecomp_commit.log`, `logs/pip_freeze.log`
- **Erwartet:** Clone (Python 3.10+, keine LLVM/CMake-Toolchain) + Abhängigkeiten.
- **Tatsächlich:** Commit `d1319ed8b7486c7a21622c811b3b41003a93d7c1`; `.venv` mit
  capstone 5.0.9, pefile 2024.8.26, lief 1.0.0, unicorn 2.1.4, cryptography 50.0.2, cffi 2.1.1.
- **Abweichung:** Repo hat **keine** `requirements.txt` → Abhängigkeiten explizit installiert.

### 2.2 Sektionen als Daten markieren (PE-Patch)

- **Befehl:** `python scripts/patch_sections.py Juiced.exe build\Juiced.pcrecomp.exe .securom .data`
- **Log:** `logs/patch_sections.log`
- **Erwartet:** `.securom` und `.data2` sind **kein** Code mehr (kein CODE/EXEC-Flag).
- **Tatsächlich:** `.securom` 0xE0000020 → 0xC0000000; `.data2` 0xE0000040 → 0xC0000040.
  Nur die Section-Header-Flags geändert, Bytes/Adressen unverändert.
- **Abweichung:** **Nötig** — `disasm32` behandelt jede Sektion mit
  `characteristics & 0x20000020` als Code. `.securom` (CODE) und `.data2` (EXEC) würden
  sonst als Code linear gescannt. Ohne den Patch lief der vorige Lauf in eine
  Speicher-Explosion (11,9 GB, kein Fortschritt) durch Pseudo-Funktionen in `.data2`.
  (Widerspricht der früheren Annahme in E3, pcrecomp überspringe diese Bereiche „automatisch".)

### 2.3 PE-Analyse

- **Befehl:** `python pcrecomp\tools\pe\pe_analyze.py build\Juiced.pcrecomp.exe --json juiced_pe.json`
- **Log:** `logs/pe_analyze.log`
- **Erwartet:** JSON mit Sektionen, Imports, Exports.
- **Tatsächlich:** 211 Imports aus 12 DLLs (advapi32, binkw32, d3d9, dinput8, dsound,
  gdi32, kernel32, ole32, shell32, user32, ws2_32, wsock32); Code-Range 0x00401000–0x02144000.
- **Abweichung:** —

### 2.4 Disassemblierung

- **Befehl:** `python pcrecomp\tools\disasm\disasm32.py build\Juiced.pcrecomp.exe --output juiced_functions.json --pe-json juiced_pe.json`
- **Log:** `logs/disasm32.log`
- **Erwartet:** Funktionskatalog JSON.
- **Tatsächlich:** **59.554 Funktionen** (1.856 Thunks, 35.765 Leafs), 7.264.206
  Instruktionen, Byte-Abdeckung 5.591.814 / 30.683.136 (18,2 %), Katalog 16.613.190 B.
  Laufzeit ~19 min, RAM-Spitze 3,7 GB.
- **Abweichung:** Erster Versuch (ungepatchte EXE) erzeugte 32.960 Kandidaten, lief bei
  22.000 fest und blähte den RAM auf 11,9 GB → abgebrochen. Nach dem Patch (2.2): 30.852
  Kandidaten, 3,7 GB, stabiles Ende nach 22 Discovery-Runden. `disasm32` hat **keine**
  Scan-Bereichs-Option; die Begrenzung erfolgt über die Section-Flags der Input-EXE.

### 2.5 Lift

- **Befehl:** *(workdir `pcrecomp`)* `python -m tools ..\build\Juiced.pcrecomp.exe --all --output ..\juiced_lifted --split 500`
- **Log:** `logs/lift.log`
- **Erwartet:** C-Quelldateien, `recomp_funcs.h`, `recomp_dispatch.c`.
- **Tatsächlich:** **59.554 Funktionen** in 1204,9 s (~20 min). **120** Quelldateien
  (`recomp_0000.c`–`recomp_0119.c`, `--split 500`) + `recomp_funcs.h` + `recomp_dispatch.c`,
  zusammen **772,7 MB** C. **0** Lift-Fehler (keine `/* ERROR ... */`-Zeilen).
- **Abweichung:** Der `python -m tools --all`-Pfad wiederholt die Discovery in-process
  (Log gepuffert → Fortschritt erst am Ende). `--functions-json` **exportiert** nur eine
  Zusammenfassung ohne Instruktionen, ist also **nicht** als Lift-Eingabe verwendbar.

---

## Phase 3 — Build und PoC

### 3.1–3.3 Runtime + CMake-Build

- **Tatsächlich:** *(folgt)*

### 3.4 PoC (difftest)

- **Befehl:** `python tools/lift/difftest.py Juiced.exe --function 0x401000`
- **Log:** `logs/difftest.log`
- **Tatsächlich:** *(folgt)*
