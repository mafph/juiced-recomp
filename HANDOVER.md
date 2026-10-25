# HANDOVER — Juiced.exe Rekompilierung (Stand sichern / PC-Umzug)

Diese Datei ist der Einstiegspunkt nach einem **PC-Neuaufbau** oder wenn der Projektordner
verschoben wird. Sie beschreibt, was im Git-Repo steckt, was nur lokal liegt (und wie es
regeneriert wird) und wie man den Stand wieder lauffähig macht.

> **Kurz:** Der Quellcode + Doku + Skripte liegen in Git (klein). Die großen Daten
> (`Juiced.exe`, `juiced_lifted/`, `build/`, `ghidra_proj/`, `tools/`) sind bewusst
> gitignored — `Juiced.exe` und der Ghidra-Export müssen mitgesichert werden, der Rest ist
> per Skript reproduzierbar. `scripts\make_snapshot.ps1` baut ein kompaktes Backup.

## 1. Was ist der Stand?

| Phase | Inhalt | Status |
|---|---|---|
| 0 | Grundlagen, Git, Umgebung | fertig |
| 1 | Ghidra-Analyse + C-Export (`decompiled/`) | fertig |
| 2 | pcrecomp: PE-Patch, Disasm (59.554 Fn), Lift (120 TUs) | fertig |
| 3.1 | Runtime-`main`: echtes Image + Stack/TIB + EP-Import-Trace | **Meilenstein erreicht** |
| 3.2/3.3 | Ninja-Vollbau → `build\juiced_full.exe` (i386) | fertig |
| 3.4 | Ein-Funktions-Difftest gegen echten Code (bit-genau) | fertig |

Details: `docs/reproduktion.md`, `docs/entscheidungen.md` (E1–E15), `AUFTRAG.md`.

Aktuellster Commit: `dad29b8` (Phase 3.1).

## 2. Was ist in Git vs. nur lokal?

**In Git (36 Dateien, ~0,2 MB `.git`):** `AUFTRAG.md`, `HANDOVER.md`, `docs/`, `scripts/`,
`poc/*.c`, `logs/.gitkeep`, `opencode.json`, `.gitignore`, `.gitattributes`.

**Gitignored, aber** (teilweise) **unersetzlich:**

| Pfad | Größe | Nötig? | Wiederherstellung |
|---|---|---|---|
| `Juiced.exe` | 28,7 MB | **ja** (Ziel-Binary) | nur aus Original-Quelle; SHA256 s. u. |
| `decompiled/` | 19,1 MB | sehr hilfreich | Ghidra-Export erneut (langsam) |
| `pcrecomp/` | 3,3 MB | **ja** | `git clone` @ `d1319ed8…` |
| `juiced_pe.json` | 30 KB | ja | `scripts\pe_analyze.py` |
| `juiced_functions.json` | 15,8 MB | ja | `disasm32` (Minuten) |
| `logs/` | 0,3 MB | Doku/Belege | teils neu erzeugbar |
| `juiced_lifted/` | 771,5 MB | nein | `translator` (Minuten) |
| `build/` | ~1,0 GB | nein | `scripts\build_full.cmd` (~13 min) |
| `ghidra_proj/` | 353,9 MB | nein | Ghidra-Import (langsam) |
| `tools/` | 1,4 GB | nein | Ghidra + Downloads erneut |
| `.venv/` | 104,2 MB | nein | `pip install` (s. u.) |

**SHA256 `Juiced.exe`:**
`9279BBF62CC1A79EE7B4E17D15DCAC56FFD63D63D06F115FD3F182C1F63D4B35`
(MD5 `0bce41a752fc18013d16010c161d36f9`, 30.097.408 Bytes)

## 3. Kompaktes Backup erzeugen (empfohlen vor Neuinstallation)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\make_snapshot.ps1
```

Ergebnis: `..\juicedDecomp_snapshot_<YYYYMMDD>\` **und** `..\juicedDecomp_snapshot_<YYYYMMDD>.zip`
neben dem Projektordner. Inhalt:

- `juicedDecomp-history.bundle` — **komplette Git-Historie** (kein Remote vorhanden!)
- `source.zip` — alle getrackten Dateien des aktuellen Commits
- `data/` — `Juiced.exe`, `juiced_pe.json`, `juiced_functions.json`, `decompiled/`,
  `pcrecomp/` (inkl. `.git`), `logs/`, `opencode.json`
- `MANIFEST.txt` — Größen + SHA256 aller Bestandteile, Tool-/Paketversionen
- `RESTORE.md` — Kurzanleitung (Kopie der relevanten Abschnitte dieser Datei)

> Das ZIP wird mit `tar`/bsdtar erzeugt. `Compress-Archive` **nicht** verwenden: es lässt
> versteckte Verzeichnisse wie `pcrecomp/.git` weg.

Danach `juicedDecomp_snapshot_<YYYYMMDD>.zip` (ca. 10–11 MB) auf einen externen Datenträger
kopieren. Der komplette Projektordner (~3,7 GB) kann alternativ 1:1 mitgenommen werden; dann
entfällt der Wiederaufbau von `build/`, `juiced_lifted/`, `tools/`, `ghidra_proj/`, `.venv/`.

## 4. Wiederherstellung auf dem neuen PC

### 4.1 Git-Historie

```powershell
git clone juicedDecomp-history.bundle juicedDecomp
# oder aus dem kompletten Ordner:
git status   # muss sauber sein
```

### 4.2 Toolchain (Windows, MSYS2)

```powershell
# MSYS2 installieren, dann in einer MSYS2-MinGW32-Shell:
pacman -S mingw-w64-i686-gcc mingw-w64-i686-cmake mingw-w64-i686-ninja mingw-w64-i686-ccache
```

Verifiziert: gcc **16.2.0**, cmake 4.4.4, ninja 1.13.2, ccache 4.14.1.
Pfad: `C:\msys64\mingw32\bin` (muss im `PATH` stehen, sonst stirbt `cc1.exe` still).

### 4.3 Python + pcrecomp

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install capstone==5.0.9 cffi==2.1.1 cryptography==50.0.2 lief==1.0.0 pefile==2024.8.26 pycparser==3.11 unicorn==2.1.4
git clone https://github.com/<pcrecomp-remote> pcrecomp
git -C pcrecomp checkout d1319ed8b7486c7a21622c811b3b41003a93d7c1
```

> `pcrecomp` ist im Snapshot enthalten; alternativ obigen Commit auschecken. Es gibt **kein**
> `requirements.txt` — die Liste oben ist `pip freeze`.

### 4.4 Daten wiederherstellen

`Juiced.exe` (Hash prüfen!), `juiced_pe.json`, `juiced_functions.json`, `decompiled/`,
`pcrecomp/`, `logs/` aus `data/` an die gleichen Pfade kopieren.

### 4.5 Reproduzieren

```bat
scripts\reproduce.cmd
```

bzw. einzeln:

```bat
scripts\build_full.cmd          :: Patches -> Ninja -> build\juiced_full.exe (~13 min)
scripts\run_image.cmd           :: Runtime-Test (Phase 3.1)
python scripts\difftest_fn.py 0x0049C682 --reg edx=0x12345678   :: Difftest
```

## 5. Kritische Stolperfallen (aus E1–E15)

- **PATH:** `C:\msys64\mingw32\bin` zuerst; sonst fehlen `cc1`/`ccache`-DLLs → stiller Exit 1.
- **cc1-OOM:** `scripts\patch_cc1_laa.py` setzt LARGE_ADDRESS_AWARE in `cc1.exe`/`cc1plus.exe`.
- **pcrecomp-x87:** `scripts\patch_recomp_weak.py` (`section(".data")` für `g_st_i64`), sonst
  überlappt der weak-Speicher die Register-Globals.
- **Undefinierte Labels:** `scripts\patch_undefined_labels.py` nach dem Lift.
- **Link-Stubs:** `scripts\gen_link_stubs.py` (weak-Stubs für fehlende `sub_*`); Liste in
  `logs\link_stubs.txt`. GNU `ld` ~165 s, kein funktionierendes i686-`lld`.
- **`native32` ist MSVC-x86-only** — unter MinGW nicht baubar; Runtime nutzt `recomp32` +
  `image_loader.c`.
- **Host-Base:** Host-Exe hoch linken (`-Wl,--image-base,0x10000000`), sonst Kollision mit
  Ziel-VA `0x00400000`.
- **Stack/TIB sind Gast-VAs:** `g_esp = HOST2GUEST(...)`, `g_fs_base` → simulierte TIB;
  sonst landet `ADDR(esp)`/`fs:[0]` neben dem Mapping.
- **IAT ist bound-imported:** auf Platte stehen absolute XP-Adressen (z. B. `0x7C812B6E`);
  Import-Namen über `scripts\iat_names.py` auflösen.
- **Deutsches Windows:** `netstat` meldet `ABHÖREN`; `timeout` scheitert bei umgeleitetem
  stdin → `ping -n 3 127.0.0.1 >nul`.

## 6. Nächster Schritt (nach Wiederherstellung)

**Import-Bridge:** IAT-Slots auf Host-Funktionen/Stubs mit bekanntem stdcall-`argc` umbiegen,
danach EP `0x005CD316` weiterlaufen lassen und die Importfolge protokollieren.
Siehe `docs/reproduktion.md` §3.6, `docs/entscheidungen.md` E15.
