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
- ~13.968 Funktionen, ~1.062.086 Instruktionen, 12 Memory Blocks.
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

| Runtime | Beschreibung | Einsatz |
|---|---|---|
| `recomp32` | 32-Bit, global registers | Standard |
| `recomp32_cpu` | 32-Bit, explizite CPU-Struct, reentrant | hybrid-Builds |
| `native32` | 32-Bit-Host, Imports gehen ans echte Windows | **Juiced** (keine DLL-Stubs) |
| `hybrid` | Lifted ↔ real boundary, CRT/MFC real | wenn CRT/MFC gebraucht wird |

Empfehlung für Juiced: `recomp32` + `native32`. Die Imports
(KERNEL32, USER32, D3D9, DSOUND, DINPUT8, WS2_32, OLE32, BINKW32) gehen ans echte
Windows — keine DLL-Stubs nötig.
