# Auftrag (korrigiert): Juiced.exe — x86 → x86 Rekompilierung

## Phase 0: Grundlagen klären

Ziel: Die korrigierten Annahmen als verbindliche Grundlage festschreiben.

- pcrecomp ist **Python (3.10+)** – keine LLVM/CMake/Ninja-Toolchain. Abhängigkeiten: `capstone` (Pflicht), `pefile`, `lief`, `unicorn`, `cryptography`.
- pcrecomp nutzt **nicht** das Ghidra-Projekt. Es disassembliert die EXE selbst via capstone. Die Ghidra-Bereinigung (Phase 1) ändert den pcrecomp-Input nicht. Für pcrecomp zählt nur: `disasm32` rekursiert vom Entry/Exports; `.securom` und Nullsektion werden nicht erreicht, solange sie nicht aufgerufen werden. `analyze_sections.py` erkennt SecuROM.
- Die korrigierten CLI-Kommandos:
  - `python tools/pe/pe_analyze.py Juiced.exe --json …`
  - `python tools/disasm/disasm32.py …`
  - `python -m tools Juiced.exe --all --output …` (das ist `translator.py`, der einzige Lifter-CLI)
- pcrecomp bringt die passenden Bausteine:
  - `runtime/native32` – 32-Bit-Host, Imports gehen ans echte Windows, keine DLL-Stubs nötig
  - `runtime/recomp32` / `recomp32_cpu` – 32-Bit-Laufzeit
  - `hybrid` – CRT/MFC real lassen
  - `lift/difftest.py` (Unicorn) für den PoC

## Phase 1: Ghidra-Bereinigung

Ziel: Müll-Funktionen aus `.securom` und der Nullsektion entfernen, diese Sektionen als Daten markieren. **Wichtig:** Das dient dem Verständnis und der späteren Arbeit – pcrecomp wird dadurch nicht beeinflusst.

> **MCP-Hinweis (pyghidra-mcp 0.2.7):** Verfügbar sind u. a. `list_project_binaries`, `list_project_binary_metadata`, `decompile_function`, `disassemble`, `read_bytes`, `list_xrefs`, `search_symbols_by_name`, `search_strings`, `set_comment`, `rename_function`, `save`. **Nicht** verfügbar: `clear` (Löschen von Funktionen/Instruktionen) und `list_functions`. Für das Löschen/Markieren von Bereichen daher ein **eigenes Ghidra-Headless-Skript** verwenden (z. B. PostScript Java/Python) – oder die Ghidra-Skripte aus pcrecomp (`tools/ghidra/*.java`: range disassembly, function bounds, export functions).

1. **Sektionsgrenzen verifizieren** (MCP: `list_project_binary_metadata`).
2. **Stichproben aus .text1 prüfen** (MCP: `decompile_function`, `disassemble`, `read_bytes`).
3. **.data2 klassifizieren** – ist dort echter Code oder nur Daten/Sprungtabellen? (MCP: `disassemble`, `list_xrefs`).
4. **Müll entfernen**: `.securom` + Nullsektion als Daten markieren, Funktionen löschen (MCP: `set_comment`; Löschen via Headless-Skript).
5. **Ergebnis verifizieren**: Funktionszahl prüfen → erwartete Zahl ~11.700–11.900 (via Headless-Skript bzw. Export-Zählung).
6. **Sauberer Re-Export** (nur als Referenz, nicht als pcrecomp-Input).

## Phase 2: pcrecomp — x86 → x86

Ziel: Die Juiced.exe mit pcrecomp in portablen C-Code liften. Kein x64, keine Architekturänderung.

### Schritt 2.1 — pcrecomp beschaffen

```bash
git clone https://github.com/sp00nznet/pcrecomp
cd pcrecomp
# ACHTUNG: Der Clone hat KEINE requirements.txt. Versionen siehe docs/umgebung.md.
pip install capstone pefile lief unicorn cryptography
```

Deps prüfen: `capstone`, `pefile`, `lief`, `unicorn`, `cryptography`.

### Schritt 2.2 — PE-Analyse (Phase "Analyse")

```bash
python tools/pe/pe_analyze.py Juiced.exe --json juiced_pe.json
```

Erwartetes Ergebnis: Header, Sektionen, Imports, Exports als JSON.

Optional: `python tools/pe/analyze_sections.py Juiced.exe` → Packing/DRM-Erkennung (SecuROM).

### Schritt 2.3 — Disassemblierung (Phase "Find functions")

```bash
python tools/disasm/disasm32.py Juiced.exe --output juiced.disasm
```

Wichtig: `disasm32` ist rekursiver Descent vom Entry Point, Exports und `--seed-functions`. Die `.securom`-Sektion und die Nullsektion werden nicht erreicht, solange sie nicht aufgerufen werden.

Optional für bessere Abdeckung:

- `python tools/cpp/rtti.py` → RTTI/vtables
- `python tools/disasm/callgraph.py` → Aufrufgraphen
- `python tools/lift/recover.py` → verpasste Einstiegspunkte

### Schritt 2.4 — Lift (Phase "Lift")

Der einzige Lifter-CLI ist `translator.py`:

```bash
python -m tools Juiced.exe --all --output juiced_lifted/
```

Das ist die Standard-32-Bit-Pipeline: analyse → disassemble → lift → split into files.

Alternative (falls nötig):

- `python tools/lift/lift32.py` → Library (global registers)
- `python tools/lift/lift32_cpu.py` → Library (CPU struct, reentrant, für hybrid builds)

Erwartetes Ergebnis: C-Dateien mit allen gelifteten Funktionen.

## Phase 3: Build und PoC

### Schritt 3.1 — Runtime wählen

pcrecomp bietet zwei 32-Bit-Runtimes:

| Runtime | Beschreibung | Wann |
|---|---|---|
| `recomp32` | 32-Bit, global registers | Standard |
| `recomp32_cpu` | 32-Bit, explizite CPU-Struct, reentrant | Für hybrid builds |
| `native32` | 32-Bit-Host, Imports gehen ans echte Windows | Für Juiced (keine DLL-Stubs nötig) |
| `hybrid` | Lifted ↔ real boundary, CRT/MFC real | Wenn CRT/MFC gebraucht wird |

Empfehlung für Juiced: `recomp32` + `native32`. Die Imports (KERNEL32, USER32, D3D9, DSOUND, DINPUT8, WS2_32, OLE32, BINKW32) gehen ans echte Windows – keine DLL-Stubs nötig.

> **Korrektur (E15):** `native32` ist unter MinGW **nicht baubar** (MSVC-x86-only, `#error` in
> `native32.c`); `win32hle` zielt auf SDL2/POSIX. Umgesetzt ist daher **`recomp32` + der generische
> PE-Loader `image_loader.c`**: `poc\runtime_main.c` mappt das echte Image (Rebase über
> `g_mem_base`), richtet einen Stack ein und führt geliftete Funktionen aus. Host-Exe hoch gelinkt
> (`-Wl,--image-base,0x10000000`). Aufruf: `scripts\run_image.cmd`. Ergebnis: Blätter mit absoluten
> Global-Zugriffen laufen korrekt; der EP 0x005CD316 läuft durch den SEH-Prolog (simulierte TIB via
> `g_fs_base`) und erreicht die ersten echten Importe `kernel32!GetVersionExA` /
> `kernel32!GetModuleHandleA`. Die IAT ist **bound-imported** (absolute XP-Adressen statt
> RVAs/Namen) — die Import-Bridge ist die nächste Stufe. Details: `docs/reproduktion.md` §3.6,
> `docs/entscheidungen.md` E15; Import-Namen löst `scripts/iat_names.py` auf.

### Schritt 3.2 — Build (Rohling) — korrigiert

> **Korrektur:** pcrecomp liefert **kein** `--generate-build-tree` (und `lift/generate.py`
> erzeugt keinen Build-Tree, sondern nur die `recomp_*.c`). Der verifizierte Weg ist ein
> Skript-Build der gelifteten C-Dateien.

Voraussetzungen: MSYS2 **MinGW32**-GCC (`mingw-w64-i686-gcc`, `C:\msys64\mingw32\bin\gcc.exe`)
und die Python-Helfer unter `scripts\`.

```bat
scripts\build_full.cmd
```

Ablauf: PE-/Header-Patches (`patch_cc1_laa.py`, `patch_recomp_weak.py`,
`patch_undefined_labels.py`) → `gen_build_ninja.py` erzeugt `build\build.ninja` →
`ninja -f build\build.ninja -j12` (parallel, inkrementell, mit ccache). Die Link-Stubs für
undefinierte `sub_*` entstehen als Ninja-Regel **nach** dem Kompilieren
(`gen_link_stubs.py` → `logs/link_stubs.txt`).

Ergebnis: **`build\juiced_full.exe`** (32-Bit-PE, machine `0x014C`). Zeiten (12 Kerne):
Kalt-Vollbau 12,9 min, inkrementell 2,9 min — Details in `docs/reproduktion.md` §3.3b/3.3c.

### Schritt 3.3 — CMake-Build (zurückgestellt)

Ein CMake-Build ist **noch nicht** der Weg: pcrecomp liefert nur
`templates/CMakeLists.txt.template`, und die `runtime/`-Ordner haben **keine** CMakeLists.
CMake lohnt sich erst, wenn der Rohling steht und einzelne Funktionen **manuell** ersetzt/
optimiert werden (dann selektiver Build statt Monolith). Bis dahin gilt der Ninja-Skript-Build
aus Schritt 3.2.

### Schritt 3.4 — PoC: Eine Funktion end-to-end

Ziel: Eine einfache Funktion aus `.text1` auswählen, liften, kompilieren, ausführen.

Kriterien: Keine DLL-Aufrufe, keine berechneten Sprünge, reine Berechnung.

Verifikation mit `difftest.py`:

```bash
python tools/lift/difftest.py Juiced.exe --function 0x401000
```

> **Korrektur:** Diesen Aufruf gibt es nicht. `difftest.py` nimmt **kein** Exe-/Funktions-
> Argument, sondern prüft einen festen Instruktions-Corpus (368 Fälle) gegen Unicorn
> (Lifter-PoC). Für einen Juiced-Funktions-PoC braucht es einen eigenen Differenz-Harness
> (geliftete Blattfunktion vs. Unicorn; Blätter findet `tools/disasm/callgraph.py`).
>
> **Umgesetzt (E14, `scripts/difftest_fn.py` + `scripts/find_leaf.py`):** Differenz-Harness
> steht; echte Juiced-Blätter (Register-only, Speicher-lesend/stdcall, verzweigend) stimmen
> bit-genau mit Unicorn/Hardware. Details: `docs/reproduktion.md` §3.5, `docs/entscheidungen.md`
> E14. Offen (nächste Stufe): absolute Speicheroperanden (Image-Mapping) und eingebettete `ret`.

Das bleibt der entscheidende Test: geliftetes C vs. Unicorn für x86-32 – jedes Register, jedes Flag, jedes Byte.

## Was nicht gemacht wird

- Kein x64. Kein Zeigerumbau, keine ABI-Anpassung.
- Kein manuelles Portieren aller 11.000+ Funktionen. `translator.py` macht die Massenarbeit.
- Kein DLL-Ersatz. Die Importe laufen über eine noch zu bauende Import-Bridge
  (`recomp32` + IAT-Slots); `native32` scheidet aus (MSVC-only).
- Kein Liften der `.securom`-Sektion. Sie wird per PE-Flag-Patch (E9) aus dem Scan genommen;
  `disasm32` selbst würde sie sonst mitlesen.

## Risiken (korrigiert)

- pcrecomp ist experimentell: Bei SEH, TLS und berechneten Sprüngen kann es scheitern. Der NFSU2-Fork hat Erweiterungen.
- BinkW32: Proprietär, 32-Bit. Eine spätere Import-Bridge müsste den Import an das echte
  Windows weiterleiten – wenn BinkW32 auf dem System vorhanden ist. Ohne BinkW32-DLL läuft
  kein Video.
- `.data2`: Falls dort Code liegt, der von `disasm32` nicht erreicht wird, fehlen Funktionen im Lift. `lift/recover.py` kann helfen.
