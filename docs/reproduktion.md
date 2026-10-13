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
- **Erwartet:** Funktionen in `.securom` + unbenannter Sektion entfernt, als Daten markiert.
- **Tatsächlich:** *(folgt)*
- **Abweichung:** pyghidra-mcp 0.2.7 hat kein `clear` → Headless-Skript statt MCP.

### 1.5 Bereinigung verifizieren

- **Tatsächlich:** *(folgt)*

### 1.6 Sauberer Re-Export

- **Befehl:** `scripts\run_export.cmd`
- **Tatsächlich:** *(folgt)*

---

## Phase 2 — pcrecomp (x86 → x86)

### 2.1 pcrecomp beschaffen

- **Befehl:** `git clone https://github.com/sp00nznet/pcrecomp` + `pip install -r requirements.txt`
- **Erwartet:** Clone + Abhängigkeiten vorhanden.
- **Tatsächlich:** *(folgt)*
- **Abweichung:** —

### 2.2 PE-Analyse

- **Befehl:** `python tools/pe/pe_analyze.py Juiced.exe --json juiced_pe.json`
- **Log:** `logs/pe_analyze.log`
- **Erwartet:** JSON mit Sektionen, Imports, Exports.
- **Tatsächlich:** *(folgt)*

### 2.3 Disassemblierung

- **Befehl:** `python tools/disasm/disasm32.py Juiced.exe --output juiced.disasm`
- **Log:** `logs/disasm32.log`
- **Tatsächlich:** *(folgt)*

### 2.4 Lift

- **Befehl:** `python -m tools Juiced.exe --all --output juiced_lifted/`
- **Log:** `logs/lift.log`
- **Tatsächlich:** *(folgt)*

---

## Phase 3 — Build und PoC

### 3.1–3.3 Runtime + CMake-Build

- **Tatsächlich:** *(folgt)*

### 3.4 PoC (difftest)

- **Befehl:** `python tools/lift/difftest.py Juiced.exe --function 0x401000`
- **Log:** `logs/difftest.log`
- **Tatsächlich:** *(folgt)*
