# Architektur

## 1. Sektionslayout der Juiced.exe

Ermittelt aus der PE-Sektionstabelle (`scripts/pe_sections.py`), ImageBase `0x400000`:

| # | Sektion | VA-Bereich (abs.) | VSize | Flags | Typ | pcrecomp |
|---|---|---|---|---|---|---|
| 1 | `.text` | 0x401000–0x6CC000 | 0x2CB000 | CODE | Code | lift N |
| 2 | `.rdata` | 0x6CC000–0x704000 | 0x38000 | Daten | Daten | Daten |
| 3 | `.data` | 0x704000–0x7A7000 | 0xA3000 | Daten | Daten | Daten |
| 4 | `.tls` | 0x7A7000–0x7A8000 | 0x1000 | Daten | Daten | Daten |
| 5 | `.rsrc` | 0x7A8000–0x7AB000 | 0x3000 | Daten | Ressourcen | Daten |
| 6 | `.text` | 0x7AB000–0xCCE000 | 0x523000 | CODE, RWX | Code | lift |
| 7 | `.init` | 0xCCE000–0xCDB000 | 0xD000 | CODE, RWX | Code | lift |
| 8 | `.data` | 0xCDB000–0xF93000 | 0x2B8000 | Daten **+ EXECUTE** | Daten/Code gemischt | prüfen |
| 9 | `.securom` | 0xF93000–0x1030000 | 0x9D000 | CODE, EXEC (verschlüsselt) | DRM-Stub | **nicht liften** |
| 10 | *(unbenannt)* | 0x1030000–0x2142000 | 0x1112000 | RW (kein Content-Flag) | 17 MB Nullen | **nicht liften** |
| 11 | `.SCY` | 0x2142000–0x2144000 | 0x2000 | CODE, EXEC | Code (8 KB) | lift |

Merkmale: Die EXE hat **zwei** `.text`-Sektionen (Nr. 1 und 6) und **zwei** `.data`-Sektionen
(Nr. 3 und 8). Die Sektion Nr. 10 hat keinen Namen; ihr Name im PE ist leer.

**Entropie (Shannon, Bytes/Byte):** nur `.securom` ist ein verschlüsselter DRM-Stub; die
restliche EXE ist DRM-frei. Das Projekt zielt **nicht** auf DRM-Umgehung.

| Sektion | Entropie | Einordnung |
|---|---|---|
| `.text` (1) | 6,56 | Code |
| `.rdata` | 5,55 | Daten |
| `.data` (3) | 3,36 | Daten |
| `.text` (6) | 6,28 | Code |
| `.init` | 6,21 | Code |
| `.securom` | 7,16 | verschlüsselt (DRM-Stub) |
| unbenannt (10) | ~0,74 | 17 MB Nullen |
| `.SCY` | 5,63 | Code (8 KB) |

### Sektions-Befunde (Phase 1)

- `.text` (Nr. 1): Stichproben (Entry `0x5CD316`, `0x401000`) sauber → valider MSVC-Code.
- `.data` (Nr. 8): überwiegend Nullen, aber ab ~`0xE80000` echte Code-Bytes und bei
  `0xE00000` als **Daten** referenziert (`FUN_0068a406`, `FUN_0068afb3`). Das EXECUTE-Flag
  führte in Ghidra zu vielen Falsch-Funktionen → **behalten**, nicht löschen.
- `.securom`: hohe Entropie (7.16), verschlüsselt, nur DRM-Stub → ausschließen.
- Sektion Nr. 10: 17 MB, Entropie ~0.74 (fast nur Nullen) → ausschließen.

## 2. Ghidra-Projekt

- Projekt: `ghidra_proj/JuicedDecomp.gpr` (Ghidra 12.1.4).
- Bildsprache: `x86:LE:32:default (4.9)`, Compiler `windows`.
- ~13.968 Funktionen (vor Bereinigung), ~1.062.086 Instruktionen, 12 Memory Blocks.
- **Nach Bereinigung (Phase 1.4):** 13.332 Funktionen (322 `.securom` + 5 unbenannt
  entfernt = 327); der Re-Export zählt 13.128 Funktionen, davon 1.726 in `.data2`
  (13.122 davon erfolgreich dekompiliert).
- Zugriff aus opencode über **pyghidra-mcp** (`http://127.0.0.1:8000/mcp`), das das
  bestehende Projekt öffnet. Der MCP-Server hält das Projekt exklusiv → für Headless-Läufe
  (Import/Analyse/Skripte) muss er zuvor gestoppt werden (`scripts/stop_mcp.cmd`).

## 3. pcrecomp-Pipeline (32-bit PE)

```
Juiced.exe (x86-32 PE)
    │
    ├── tools/pe/pe_analyze.py      → Header, Sektionen, Imports, Exports (JSON)
    ├── tools/disasm/disasm32.py    → rekursiver Descent vom Entry/Exports → Funktionen
    ├── tools/lift/lift32.py        → C (Library; global registers)
    └── tools/lift/translator.py    → CLI: analyse → disassemble → lift → Dateien splitten
    │
    ▼
C-Funktionen (eine oder mehrere Dateien)
```

Ergänzende Werkzeuge: `tools/cpp/rtti.py`, `tools/cpp/vtable_scan.py`,
`tools/disasm/callgraph.py`, `tools/lift/recover.py` (verpasste Einstiegspunkte).

**Warum `.securom`/Nullsektion nicht geliftet werden:** `disasm32` ist ein rekursiver
Descent vom Entry Point, den Exports und `--seed-functions`. Nicht erreichbare Bereiche
werden nicht dekodiert. `tools/pe/analyze_sections.py` erkennt SecuROM zusätzlich.

## 4. Runtime-Auswahl (Build)

pcrecomp liefert Laufzeiten unter `runtime/`:

| Runtime | Beschreibung | Einsatz für Juiced |
|---|---|---|
| `recomp32` | 32-Bit, globale Register | **gewählt** (mit `image_loader`) |
| `recomp32_cpu` | 32-Bit, explizite CPU-Struct, reentrant | hybrid-Builds |
| `native32` | 32-Bit-Host, Importe ans echte Windows | **nicht nutzbar**: MSVC-x86-only (`#error` in `native32.c`; Bridge/Callback-Trampolin ist Inline-Asm) |
| `win32hle` | portable Win32-HLE (Schim-ABI `A32/APTR/ASTR`, `RET/RETP`, `hle_call_guest`), per-Thread-TIB über `g_fs_base` | Option für später; SDL2/POSIX-lastig, braucht Host + `pe_loader` |
| `hybrid` | Lifted ↔ real boundary, CRT/MFC real | wenn CRT/MFC gebraucht wird |

**Entscheidung (E15):** `recomp32` + der generische PE-Loader
`runtime/recomp32/image_loader.c`. `native32` scheidet unter MinGW aus; `win32hle` ist
zwar portabel, zieht aber einen POSIX/SDL2-Host nach sich. Die Runtime mappt das
Original-Image selbst und führt gelifteten Code gegen echte Daten aus.

Importierte DLLs (211 Importe aus 12 DLLs): advapi32, binkw32, d3d9, dinput8, dsound,
gdi32, kernel32, ole32, shell32, user32, ws2_32, wsock32.

## 5. Speicher- und Aufrufmodell der Runtime

Der geliftete Code rechnet **jede** Gast-Adresse über die Runtime:

| Baustein | Bedeutung |
|---|---|
| `ADDR(va)` | `(uintptr_t)(uint32_t)va + g_mem_base` — einziger Weg in den Gast-Speicher |
| `MEM32/MEM16/MEM8(va)` | `*(volatile …*)ADDR(va)` |
| `g_mem_base` | Rebase-Offset: `gewaehlte_base - 0x400000` |
| `g_eax … g_ebp` | globale Register (bei `RECOMP_GENERATED_CODE` ohne `RECOMP_LOCAL_REGS`) |
| `g_st[8]`, `g_fp_top`, `g_fpu_cw` | gemeinsamer x87-Schattenspeicher |
| `RECOMP_ENTER(va)` | setzt `g_cur_func` + `RECOMP_FLAGS_IN()` |
| `RECOMP_CALL(fn)` | direkter Aufruf einer bekannten gelifteten Funktion |
| `RECOMP_ICALL(va)` | `recomp_lookup(va)` → `recomp_lookup_import(va)`; sonst Log |
| `RECOMP_RETADDR` | `0xDEAD0000` (Marker für synthetische Rücksprungadresse) |
| `g_icall_trace/from/idx/count` | Ringpuffer, `ICALL_TRACE_SIZE = 128` |

**Wichtige Konsequenzen:**

- **Stack ist eine Gast-VA.** `g_esp = HOST2GUEST(host_stack_top)`, denn auch
  `MEM32(esp+…)` läuft über `ADDR`. `HOST2GUEST` nutzt bewusst den 32-Bit-Wrap
  (`host - g_mem_base`).
- **`fs:` wird modelliert.** `FS_BASE` ist `g_fs_base` (Gast-VA auf eine simulierte TIB).
  Der SEH-Prolog des EP liest/schreibt `fs:[0]`; ohne TIB landet das bei `ADDR(0)`.
  TIB-Felder: `+0x00` SEH-Terminator `0xFFFFFFFF`, `+0x04` StackBase, `+0x08` StackLimit,
  `+0x18` Self.
- **Unaufgelöster Import:** `recomp_lookup_import` liefert `NULL`; `RECOMP_ICALL` loggt
  `ICALL: unresolved VA … from …`, setzt `eax = 0` und **reinigt den Stack nicht**
  (stdcall-`argc` unbekannt). Der Aufrufer läuft weiter → möglicher ESP-Drift und späterer
  `ADDR(0)`-Zugriff, wenn der `NULL`-Rückgabewert als Zeiger benutzt wird.
- **Host-Base:** Das Host-PE wird hoch gelinkt (`-Wl,--image-base,0x10000000`), damit
  `0x00400000` für das Gast-Image frei bleibt bzw. der Rebase-Fall sauber ist.

**`image_loader` (`recomp_load_image(path, base)`):**

- parst die Sektionstabelle zur Laufzeit, reserviert/committet `span` RWX an `base`,
  kopiert Headers + Sektionen, nullt `.bss` (Sektionen mit `PointerToRawData == 0`).
- kopiert pro Sektion bis `VirtualSize` page-gerundet (nicht bis `SizeOfRawData`), begrenzt
  auf Dateigröße und `span`.
- gibt nur `span` zurück (nicht die tatsächliche Base) und **rebased nicht selbst** —
  die Base muss frei sein. Die Runtime probiert deshalb mehrere Kandidaten.

## 6. Import-Modell

- Die Import-Tabelle (`juiced_pe.json`, 211 Slots) liefert DLL + Name je IAT-Slot.
- **Die IAT ist bound-imported:** Auf Platte stehen bereits absolute Adressen des alten
  Windows-XP-Layouts (z. B. `0x7C812B6E` für `kernel32!GetVersionExA`), **keine** RVAs/Namen.
  Ein reines Sektions-Mapping kann diese Importe daher nicht auflösen.
- `scripts/iat_names.py` ordnet Slot-VA **oder** gebundene Adresse dem Importnamen zu:
  `0x6CC1EC → kernel32.dll!GetVersionExA`, `0x6CC168 → kernel32.dll!GetModuleHandleA`.
- Der EP `0x005CD316` ruft zuerst genau diese beiden Importe auf (siehe §3.6 in
  `reproduktion.md`).
- **Import-Bridge (offen):** IAT-Slots auf Host-Funktionen oder Stubs mit bekanntem
  stdcall-`argc` umbiegen. Das `argc` stammt aus den Win32-Signaturen; für unbekannte
  Importe ist ein konservativer Stub nötig (sonst ESP-Drift). Optionen: `win32hle`
  (`host_lite.c` + `pe_loader.c`) oder `recomp32` + eigene Stub-Tabelle.

## 7. Datenmodelle und Kataloge

| Datei | Inhalt | Größe |
|---|---|---|
| `juiced_pe.json` | PE-Analyse: Sektionen, 211 Importe/12 DLLs, Exports | 48.678 B |
| `juiced_functions.json` | Funktionskatalog aus `disasm32` | 16.613.190 B |
| `decompiled/all_functions.c` | Ghidra-Referenzdekompilat | 19.504.879 B |
| `decompiled/functions.csv` | Funktionsliste des Exports | 522.944 B |

**`juiced_functions.json`:**

- Top-Level: `exe`, `image_base` (4194304), `code_start` (4198400), `code_end` (34881536),
  `iat_count` (211), `stats`, `functions`.
- `stats`: `functions 59554`, `thunks 1856`, `leaves 35765`, `instructions 7264206`,
  `covered_bytes 5591814`, `code_bytes 30683136`, `coverage_pct 18.22`.
- pro Funktion: `address`, `address_hex`, `name`, `end`, `size`, `num_blocks`,
  `num_instructions`, `is_thunk`, `entry_kind`, `calls_to`.
- `entry_kind == "start"` und `calls_to == []` ⇒ Blattfunktion.

**`decompiled/functions.csv`:** Header `entry,name,size,numParams,isThunk,decompiled`
(13.129 Zeilen inkl. Header = 13.128 Funktionen).
