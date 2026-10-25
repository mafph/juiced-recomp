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

`capstone` (Pflicht), `pefile`, `lief`, `unicorn`, `cryptography`.
**Achtung:** Der pcrecomp-Clone hat **keine** `requirements.txt`; die exakten Versionen
stehen in `docs/umgebung.md` (`pip freeze`).

## Wichtige Grundregeln (siehe `docs/entscheidungen.md`)

- pcrecomp nutzt **nicht** das Ghidra-Projekt — es disassembliert die EXE selbst.
- `.securom` (verschlüsselt) und die 17-MB-Nullsektion werden **nicht** geliftet.
- `.data2` wird **nicht** blind gelöscht (enthält echten Code und Daten).

## Verzeichnisstruktur

```
juicedDecomp/
├── AUFTRAG.md            # der Auftrag
├── HANDOVER.md           # Restore/Umzug/Neuinstallation + Snapshot
├── docs/                 # technische Dokumentation (diese)
├── logs/                 # Logs jedes Schritts (gitignored, nur .gitkeep)
├── scripts/              # Automatisierung + Reproduktion
│   ├── reproduce.cmd     # Windows-Reproduktion (alle Schritte)
│   ├── reproduce.sh      # Linux-Reproduktion
│   ├── build_full.cmd    # Vollbau (Ninja, alle 120 TUs)
│   ├── run_image.cmd     # Phase 3.1: Runtime-Test (Image + gelifteter Code)
│   ├── make_snapshot.ps1 # portables Backup (Git-Bundle + Daten)
│   ├── pe_sections.py    # PE-Sektionstabelle parsen
│   ├── run_analyze.cmd   # Ghidra-Headless Import+Analyse
│   ├── run_export.cmd    # Ghidra-Headless C-Export
│   └── ...               # MCP-Steuerung, Patches, Build-Generatoren
├── poc/                  # Runtime-Einstiege
│   ├── main.c            # Smoke-Einstieg (nur Link-/Toolchain-Nachweis)
│   └── runtime_main.c    # echtes Image + Stack/TIB + EP-Aufruf
├── pcrecomp/             # pcrecomp-Clone (gitignored, commit-gepinnt)
├── juiced_lifted/        # geliftete C-TUs (gitignored, regenerierbar)
├── build/                # Objekte + EXEs (gitignored)
├── ghidra_proj/          # Ghidra-Projekt (gitignored)
├── decompiled/           # Ghidra-C-Export (gitignored)
├── tools/                # Ghidra-Installation (gitignored)
├── .venv/                # Python-Umgebung (gitignored)
└── Juiced.exe            # Ziel-Binary (gitignored)
```

## Dokumentation

| Datei | Inhalt |
|---|---|
| `docs/README.md` | Einstieg, Ziel, Struktur |
| `docs/architektur.md` | PE-Layout, Pipeline, **Speicher-/Aufrufmodell**, Import-Modell, Datenmodelle |
| `docs/reproduktion.md` | jeder Schritt: Befehl, Erwartung, Ist, Abweichung |
| `docs/entscheidungen.md` | ADRs E1–E15 |
| `docs/werkzeuge.md` | CLI-Referenz + bekannte Werkzeug-Quirks |
| `docs/offene-punkte.md` | nächste Schritte + bekannte Grenzen |
| `docs/umgebung.md` | Versionen, Pfade, System-Quirks |
| `HANDOVER.md` | Umzug/Neuinstallation, Snapshot, Restore |

**Repository:** <https://github.com/mafph/juiced-recomp> (öffentlich, Branch `main`).
Dort liegen nur Quellen/Doku/Skripte; die großen Daten stehen im Snapshot (siehe `HANDOVER.md`).

## Reproduktion

Siehe `docs/reproduktion.md`. Kurz: `scripts\reproduce.cmd` (Windows) bzw.
`bash scripts/reproduce.sh` (Linux) ausführen — setzt Python, Ghidra 12.1.4 und
das Ziel-Binary voraus.
