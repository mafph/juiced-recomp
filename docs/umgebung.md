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
| MSYS2 + pacman | — | `C:\msys64\` |
| mingw-w64-i686-gcc (32-bit) | 16.2.0 | `C:\msys64\mingw32\bin\gcc.exe` (Target `i686-w64-mingw32`) |
| CMake | 4.4.4 | `C:\msys64\mingw32\bin\cmake.exe` |
| Ninja | 1.13.2 | `C:\msys64\mingw32\bin\ninja.exe` |
| 64-bit-gcc (nur difftest) | 15.2.0 | `C:\msys64\ucrt64\bin\gcc.exe` (Target `x86_64-w64-mingw32`) |

## pcrecomp

| | |
|---|---|
| Repo | https://github.com/sp00nznet/pcrecomp |
| Commit | `d1319ed8b7486c7a21622c811b3b41003a93d7c1` |
| Abhängigkeiten | capstone, pefile, lief, unicorn, cryptography |

### `pip freeze` (pcrecomp-Umgebung, `.venv`, Python 3.14.2)

```
capstone==5.0.9
cffi==2.1.1
cryptography==50.0.2
lief==1.0.0
pefile==2024.8.26
pycparser==3.11
unicorn==2.1.4
```

## Installiert (Phase 3)

Per MSYS2/pacman nachinstalliert (Repo `mingw32`), für den 32-Bit-Build der Runtime
+ des gelifteten Codes:

```
pacman -S mingw-w64-i686-gcc mingw-w64-i686-cmake mingw-w64-i686-ninja
```

MSVC 2022 ohne C++-Workload ist weiterhin nicht nutzbar; der GCC-Pfad erfordert den
Runtime-Fix `scripts/patch_recomp_weak.py` (siehe ADR E10).

## Referenz-Hashes des Ziel-Binaries

| | |
|---|---|
| Datei | `Juiced.exe` |
| Größe | 30.097.408 Bytes (~28.7 MB) |
| MD5 | `0bce41a752fc18013d16010c161d36f9` |
| SHA256 | `9279bbf62cc1a79ee7b4e17d15dcac56ffd63d63d06f115fd3f182c1f63d4b35` |
| ImageBase | `0x400000` |
| Entry Point | `0x5CD316` |
