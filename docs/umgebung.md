# Umgebung & Versionen

Stand: siehe Commit-Historie (diese Datei wird pro Schritt aktualisiert).

## System

| | |
|---|---|
| OS | Microsoft Windows 10 Home, Build 10.0.19045 |
| Architektur | AMD64 |
| PowerShell | 5.1.19041.7663 |
| Shell | cmd.exe (Skripte) |

## Werkzeuge

| Werkzeug | Version | Pfad |
|---|---|---|
| Python | 3.14.2 | `C:\Users\Marcos\AppData\Local\Python\pythoncore-3.14-64\` |
| pip | 26.2.1 | (python 3.14) |
| Git | 2.56.0.windows.2 | — |
| Java (JDK) | 24.0.1 | `C:\Program Files\Java\jdk-24` (`JAVA_HOME`) |
| Ghidra | 12.1.4 | `tools\ghidra_12.1.4_PUBLIC\` |
| pyghidra-mcp | 0.2.7 | MCP-Server auf `http://127.0.0.1:8000/mcp` |
| uv | — | `C:\Users\Marcos\AppData\Local\Python\pythoncore-3.14-64\Scripts\uv.exe` |

## pcrecomp

| | |
|---|---|
| Repo | https://github.com/sp00nznet/pcrecomp |
| Commit | *(wird beim Klonen eingetragen)* |
| Abhängigkeiten | capstone, pefile, lief, unicorn, cryptography |

### `pip freeze` (pcrecomp-Umgebung)

```
*(wird nach dem Erstellen der venv eingetragen)*
```

## Nicht installiert (relevant)

- MSVC 2022 C++-Workload (`cl`), Clang (`clang-cl`), CMake, Ninja.
  → Für Phase 3 (Build der gelifteten C-Dateien) nachzuinstallieren.

## Referenz-Hashes des Ziel-Binaries

| | |
|---|---|
| Datei | `Juiced.exe` |
| Größe | 30.097.408 Bytes (~28.7 MB) |
| MD5 | `0bce41a752fc18013d16010c161d36f9` |
| SHA256 | `9279bbf62cc1a79ee7b4e17d15dcac56ffd63d63d06f115fd3f182c1f63d4b35` |
| ImageBase | `0x400000` |
| Entry Point | `0x5CD316` |
