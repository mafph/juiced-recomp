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

### 3.1–3.3 Runtime + 32-Bit-Build

- **Erwartet:** 32-Bit-Compiler, um die Runtime `recomp32` mit dem gelifteten C
  (772,7 MB) zu einem 32-Bit-PE zu linken.
- **Vorbereitung (Toolchain):** Kein 32-Bit-Compiler vorhanden gewesen. Per MSYS2/pacman
  nachinstalliert: `mingw-w64-i686-gcc` (gcc **16.2.0**, Target `i686-w64-mingw32`),
  `mingw-w64-i686-cmake` (CMake 4.4.4), `mingw-w64-i686-ninja` (1.13.2) und
  `mingw-w64-i686-ccache` (**4.14.1**) — siehe `umgebung.md`.
  Hinweis: gcc/cc1/ccache laden ihre DLLs aus `C:\msys64\mingw32\bin`; die Build-Skripte
  setzen diesen Pfad selbst (`set "PATH=…`), da sonst `cc1.exe` **still** mit exit 1 stirbt.

#### 3.1–3.3a PoC-Smoke-Link (eine TU)

- **Befehl:** `scripts\build_poc.cmd`
- **Schritte:** `patch_recomp_weak.py` (E10) → `gen_weak_stubs.py` → i686-gcc kompiliert
  `poc\main.c` + `juiced_lifted\recomp_0000.c` (`-O0 -w -ffunction-sections`, Prototypen per
  `-include recomp_funcs.h`) → Link `-Wl,--gc-sections` gegen die weak-Stubs.
- **Tatsächlich:** **`build\juiced_poc.exe`, 14,36 MB, machine `0x014C` (i386, 32-bit)**,
  läuft, `sizeof(void*)=4`. `recomp_0000.c` (5,58 MB, 500 Fn) kompiliert in ~9 s.

#### 3.1–3.3b Vollbau (alle 120 TUs) — Ninja, parallel + inkrementell

- **Befehl:** `scripts\build_full.cmd`
- **Schritte:** `patch_cc1_laa.py` (s. u.) → `patch_recomp_weak.py` → `patch_undefined_labels.py`
  → `gen_build_ninja.py` (erzeugt `build\build.ninja`) → `ninja -f build\build.ninja -j12`.
  Kompilieren **und** Linken übernimmt Ninja; die Link-Stubs entstehen als eigene Ninja-Regel
  `stubs` **nach** dem Kompilieren (`nm` über `build\full\*.o`).
- **Tatsächlich:** **`build\juiced_full.exe`, 376,1 MB, machine `0x014C` (i386, 32-bit)**,
  läuft, `sizeof(void*)=4`.
- **Zeiten (12 Kerne, i686-gcc 16.2.0, ccache 4.14.1):**

  | Lauf | Zeit | Anmerkung |
  |---|---|---|
  | Kalt-Vollbau (120 TUs) | **12,9 min** | Objektphase ~10,2 min + Link ~2,7 min; ccache kalt (245 Misses) |
  | Inkrementell (1 TU berührt) | **2,9 min** | ccache 122/122 Hits (TU sofort), Rest Stubs+Link |

- **Auftretende Blocker (gelöst):**
  1. **`cc1.exe: out of memory`** bei den größten TUs (bis 37 MB) — der i686-`cc1` ist selbst
     32-Bit und ohne LAA auf ~2 GB begrenzt. Fix: LARGE_ADDRESS_AWARE-Bit in `cc1.exe`/`cc1plus.exe`
     setzen (`scripts/patch_cc1_laa.py`, ~4 GB auf 64-Bit-Windows) plus speicherschonende
     Parameter `--param ggc-min-heapsize=32768 ggc-min-expand=10`.
  2. **`label 'L_…' used but not defined`** (15 Dateien, 37 Labels) — Lift-Defekte des Translators
     für Sprungziele aus dem linearen Over-Scan. Fix: `scripts/patch_undefined_labels.py`
     (Label-Definition am Funktionsanfang, betrifft nur Garbage-/Dead-Code).
  3. **`implicit declaration of function`** (gcc 14+ = Fehler): nur `-Wno-error=implicit-function-declaration`.
  4. **Undefinierte `sub_*`** — 20.697 von den TUs **referenzierte** Symbole, davon **17.124
     nirgends definiert** (Ziele außerhalb des Katalogs/Images = „schwarze Löcher"). `scripts/gen_link_stubs.py`
     erzeugt dafür weak-Leer-Stubs; die vollständige Liste landet in **`logs/link_stubs.txt`**
     (Aufrufe liefern später Müll — beim Aufräumen relevant). i686-PE-Symbole tragen einen
     führenden Unterstrich (`_sub_…`).
- **Abweichungen / Hinweise:**
  - `poc\main.c` ist ein **Smoke-Einstieg** ohne Speicher-Layout/Imports — es wird **kein
    Spielcode ausgeführt**; der PoC belegt nur Übersetz- und Linkbarkeit als 32-Bit-PE.
  - `--unresolved-symbols=ignore-all` wird von diesem mingw-ld im PE-Pfad **nicht** honoriert;
    daher weak-Stubs (`gen_weak_stubs.py`/`gen_link_stubs.py`).
  - Die Stub-Erzeugung **muss nach** dem Kompilieren laufen (sie scannt die Objekte); im
    Ninja-Graph steuert das die Regel-Reihenfolge.

#### 3.3c Build-Optimierung (Parallelität, ccache, inkrementell)

- **Befehl:** `python scripts\gen_build_ninja.py` → `ninja -f build\build.ninja [-jN]`
- **Design:** Die frühere sequenzielle `for`-Schleife in `build_full.cmd` wurde durch einen
  generierten **`build.ninja`** ersetzt. Ninja kompiliert **parallel** (`-j`, Default `NINJA_J=12`)
  und **inkrementell** (nur geänderte TUs + Link). **ccache** wird als Compiler-Präfix genutzt,
  wenn `C:\msys64\mingw32\bin\ccache.exe` vorhanden ist.
- **Nur Teil-Builds / einzelne Objekte:**
  - inkrementell neu bauen: `ninja -f build\build.ninja`
  - ein Objekt: `ninja -f build\build.ninja build/full/recomp_0000.o`
  - Zustand (`.ninja_log`/`.ninja_deps`) liegt über `builddir = build` bzw. im Repo-Root
    (gitignored).
- **Ziele vs. erreicht:**
  - Vollbuild **< 15 min** → **erreicht** (12,9 min kalt).
  - Inkrementell **< 2 min** → **nicht erreicht** (2,9 min). Flaschenhals ist der
    **Single-Thread-GNU-Linker** (`ld`): **~165 s**, praktisch unabhängig von `--gc-sections`
    (mit 168 s / ohne 166 s gemessen). ccache wirkt nur auf das Kompilieren (geänderte TU =
    sofortiger Hit). Ein Ersatzlinker **LLVM `lld`** würde das lösen, ist hier aber
    **nicht lauffähig** (`ucrt64-lld` bricht mit `0xC0000139` `STATUS_ENTRYPOINT_NOT_FOUND`
    ab, wie zuvor `ucrt64-clang`; ein natives i686-`lld`-Paket existiert nicht). Workaround für
    schnelle Editier-Iteration: nur einzelne Objekte bauen.
- **`-w` versteckt Warnungen:** Gebaut wird mit `-w` (Warnungen aktuell nicht
  handlungsleitend). Sobald der PoC läuft, **einmal ohne `-w`** bauen und die Warnungen nach
  **`logs/warnings.txt`** sammeln — das ist die Prioritätenliste beim Aufräumen.

### 3.4 PoC (difftest)

- **Befehl:** `python pcrecomp\tools\lift\difftest.py` (venv-Python, `PATH` inkl.
  `C:\msys64\ucrt64\bin`; Host-Compiler ist das 64-Bit-gcc, `RECOMP_CC` optional)
- **Log:** `logs/difftest.log` (Basislauf), `logs/difftest_weakfix.log` (mit Fix)
- **Erwartet:** Alle Instruktions-PoC-Fälle stimmen mit Unicorn/Hardware überein.
- **Tatsächlich (Basislauf):** **273/368** stimmen, **0 known divergences, 95 failures** —
  **alle im x87/FPU-Bereich**. Die 95 Fälle zeigen geliftete GPR-Werte = 0.
- **Ursache (ermittelt, kein Lift-Fehler):** Im GCC-/MinGW-Pfad legt der Linker das im Header
  **weak** (`RECOMP_SHARED_DATA = __attribute__((weak))`) definierte, null-initialisierte
  Schattenarray `g_st_i64[8]` **überlappend** auf den Registerblock. Im Basis-Binary sind
  `g_eax/g_ecx/g_edx/g_esp/g_ebx` (`0x…80AC`–`0x…80BC`) in `g_st_i64` (`0x…8080`–`0x…80BF`)
  eingebettet; `g_esi/g_edi/g_ebp` liegen knapp dahinter und überleben. Jeder `fp_push`/`fp_pop`
  überschreibt damit die GPRs — in x87-Fällen sichtbar, weil sonst niemand diese Register liest.
- **Verifikation:** `scripts/patch_recomp_weak.py` verschiebt die weak-Definition in eine
  explizite Sektion (`__attribute__((weak, section(".data")))`); damit **368/368, 0 Fehler**
  (`logs/difftest_weakfix.log`) und ein Zwei-TU-Link ohne Duplikat-Fehler. Ursache konklusiv.
- **Einordnung:** Umgebungs-/Toolchain-Artefakt des GCC-Pfads (MSVC nutzt `__declspec(selectany)`).
  Relevant für einen späteren MinGW-Build des gelifteten Codes (FPU-lastige Funktionen).
- **Abweichung:** Der in Phase 2 notierte „difftest gegen eine Juiced-Funktion"-Aufruf war nicht
  korrekt — `difftest.py` nimmt **kein** Exe-/Funktions-Argument, sondern prüft eine feste
  Instruktions-Corpus (368 Fälle). Es ist damit ein **Lifter**-PoC, kein Juiced-Funktions-PoC.

### 3.5 Ein-Funktions-Difftest gegen echten Juiced-Code

Beweist, dass der Lift **echter Juiced-Funktionen** (nicht nur der Corpus) bit-genau mit dem
Original-CPU-Verhalten übereinstimmt: geliftete C-Funktion gegen Unicorn, verglichen werden alle
acht GPRs, die definierten EFLAGS (CF/PF/AF/ZF/SF/DF/OF) und der beschriebene Gast-Speicher.

- **Werkzeuge:** `scripts/find_leaf.py` (katalogisiert geeignete Blätter aus
  `juiced_functions.json`), `scripts/difftest_fn.py` (Frontend auf die Engine von
  `pcrecomp\tools\lift\difftest.py`).
- **Auswahl (`find_leaf.py`):** nur `entry_kind == "start"`, `calls_to` leer, ohne
  call/jmp/FPU/SSE/String-Ops, ohne absolute Speicheroperanden, alle Sprungziele innerhalb der
  Funktion. `--interesting` zeigt zusätzlich Funktionen mit Branches/`imul`/`div`.
- **Ausführung (`difftest_fn.py <VA>`):** Funktion wird im difftest-Gastfenster bei `BASE`
  (0x400000) emuliert/verglichen. Der abschließende `ret` wird abgeschnitten (Unicorn hält am
  Funktionsende an; beide Seiten vergleichen **vor** dem Rücksprung), sein Adress-Label bleibt
  erhalten, damit jcc dorthin als `goto` landen. `lift32` ruft für Sprünge
  `insn.get_branch_target()` (nur auf `disasm32.Instruction`, nicht auf capstone) — der Script
  reicht einen Shim nach.
- **Aufruf-Beispiele** (venv-Python, `PATH` inkl. `C:\msys64\ucrt64\bin`):
  - `python scripts\difftest_fn.py 0x0049C682 --reg edx=0x12345678`
  - `python scripts\difftest_fn.py 0x0062D21B --frame 0x412000 --arg 0x411000 --mem 0x411042=1000 --mem 0x4110a4=04030201`
  - `python scripts\difftest_fn.py 0x00C52BF8 --frame 0x412000 --reg eax=5` (und `eax=7`)
- **Ergebnis:** alle geprüften Funktionen **OK** (lifted == CPU):

  | VA | Funktion (Kategorie) | Ergebnis |
  |----|----------------------|----------|
  | 0x0049C682 | `mov eax,0xa; add eax,edx; ret 4` (nur Register + Flags) | OK |
  | 0x0062D21B | `movzx`/`imul`/`add [ecx+..]`/`not` (Speicher lesen, stdcall-Frame) | OK |
  | 0x00C52BF8 | `cmp; jne; mov [ebp-0x18],1; ret` (Branch, beide Pfade) | OK |

- **Grenzen (nächste Stufe):** Funktionen mit absoluten Speicheroperanden brauchen ein echtes
  Image-Mapping (`.rdata`/`.data` an Original-VAs); Funktionen mit eingebettetem `ret` (früher
  Rücksprung) werden derzeit abgelehnt (`difftest_fn.py` bricht mit klarer Meldung ab).


