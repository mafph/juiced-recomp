# Offene Punkte & Nächste Schritte

Bekannte Grenzen des aktuellen Stands und Roadmap für die weiteren Phasen.

## 1. Nächster Schritt: Import-Bridge (Phase 3.1 fortsetzen)

- **Befund:** Der EP `0x005CD316` läuft nach Bereitstellung von Stack und TIB (`g_fs_base`)
  erfolgreich durch den SEH-Prolog und erreicht die ersten echten IAT-Importe:
  `kernel32!GetVersionExA` (Slot `0x6CC1EC`, gebunden `0x7C812B6E`) und
  `kernel32!GetModuleHandleA` (Slot `0x6CC168`, gebunden `0x7C80B731`).
  Ein unaufgelöster Import liefert `NULL` und führt zu einem `ADDR(0)`-Zugriff.
- **Aufgabe:** IAT-Slots auf Host-Funktionen oder Stubs mit bekanntem stdcall-`argc`
  umbiegen.
  - Das `argc` stammt aus den Win32-Signaturen der jeweiligen API.
  - Für unbekannte Importe ist ein konservativer Stub (oder Logging mit Stack-Erkennung) nötig,
    um ESP-Drift zu verhindern.
  - Alternativ: Prüfung der Portierung von pcrecomps `win32hle` (`host_lite.c` + `pe_loader.c`),
    die bereits viele kernel32/user32/gdi32/dsound-Imports stubbt/leitet.

## 2. Inkrementelles Build-Ziel (< 2 min)

- Flaschenhals ist der **Single-Thread-GNU-Linker** (`ld`, ~165 s).
- ccache beschleunigt das Kompilieren (Hits), aber der Link läuft immer voll.
- **Lösung:** Sobald ein lauffähiges i686-`lld` oder ein schnellerer Linker verfügbar ist,
  in `scripts/gen_build_ninja.py` die Link-Regel umstellen (`-fuse-ld=lld`).

## 3. Warnungs-Analyse

- Der Build läuft aktuell mit `-w` (Warnungen unterdrückt).
- Sobald der EP stabil durchläuft: Einmal **ohne `-w`** bauen und die Warnungen nach
  **`logs/warnings.txt`** schreiben als Prioritätenliste für Typ- und Signatur-Bereinigungen.

## 4. Bekannte Grenzen

- **Difftest (Ein-Funktion):** Absolute Speicheroperanden erfordern ein geladenes Image
  (in `difftest_fn.py` noch nicht aktiv); Funktionen mit eingebettetem `ret` werden
  abgelehnt.
- **`native32`:** Unter MinGW nicht nutzbar (MSVC-only); wir nutzen `recomp32` + `image_loader`.
