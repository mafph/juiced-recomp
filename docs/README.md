# Juiced.exe — Statische Rekompilierung (x86 → x86)

## Ziel

Statische Rekompilierung der `Juiced.exe` (x86-32, PE, Juice Games / THQ 2005) nach
**portablem C-Code — ohne Architekturwechsel, ohne Änderung der Semantik**.
Erster, kleinster Schritt: **x86 → x86** (kein x64, keine ABI-Anpassung).

Pipeline: `Analyse → Disassemblierung → Lift → Build → PoC`.
Das Massen-Liften übernimmt **pcrecomp** (`disasm32` → `lift32`, CLI: `tools/lift/translator.py`).

## Toolchain

| Baustein | Version | Zweck |
|---|---|---|
| pcrecomp | (siehe `docs/umgebung.md`) | x86-32 PE → C (capstone-basiert) |
| Python | 3.14.2 | pcrecomp-Laufzeit |
| Ghidra | 12.1.4 | Referenz-Analyse, manuelle Inspektion |
| pyghidra-mcp | 0.2.7 | Ghidra-Zugriff aus opencode (MCP) |
| Java | 24.0.1 | Ghidra-Headless |
| Git | 2.56.0.windows.2 | Versionierung |

## pcrecomp-Abhängigkeiten

`capstone` (Pflicht), `pefile`, `lief`, `unicorn`, `cryptography`
(→ `pip install -r requirements.txt` im pcrecomp-Clone).

## Wichtige Grundregeln (siehe `docs/entscheidungen.md`)

- pcrecomp nutzt **nicht** das Ghidra-Projekt — es disassembliert die EXE selbst.
- `.securom` (verschlüsselt) und die 17-MB-Nullsektion werden **nicht** geliftet.
- `.data2` wird **nicht** blind gelöscht (enthält echten Code und Daten).

## Verzeichnisstruktur

```
juicedDecomp/
├── AUFTRAG.md            # der Auftrag
├── docs/                 # technische Dokumentation (diese)
├── logs/                 # Logs jedes Schritts
├── scripts/              # Automatisierung + Reproduktion
│   ├── reproduce.cmd     # Windows-Reproduktion (alle Schritte)
│   ├── reproduce.sh      # Linux-Reproduktion
│   ├── pe_sections.py    # PE-Sektionstabelle parsen
│   ├── run_analyze.cmd   # Ghidra-Headless Import+Analyse
│   ├── run_export.cmd    # Ghidra-Headless C-Export
│   └── ...               # MCP-Steuerung, Autostart
├── ghidra_proj/          # Ghidra-Projekt (nicht im Repo)
├── decompiled/           # Ghidra-C-Export (nicht im Repo)
├── tools/                # Ghidra-Installation (nicht im Repo)
└── Juiced.exe            # Ziel-Binary (nicht im Repo)
```

## Reproduktion

Siehe `docs/reproduktion.md`. Kurz: `scripts\reproduce.cmd` (Windows) bzw.
`bash scripts/reproduce.sh` (Linux) ausführen — setzt Python, Ghidra 12.1.4 und
das Ziel-Binary voraus.
