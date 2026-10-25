# Entscheidungen (ADRs)

Kurzformat: **Kontext → Entscheidung → Begründung → Alternativen.**

## E1 — Werkzeug: pcrecomp statt Ghidra-Decompiler oder manuellem Port

- **Kontext:** 13.968 Funktionen müssen nach C.
- **Entscheidung:** pcrecomp (`disasm32` + `lift32`).
- **Begründung:** Genau für x86-32 PE → portables C gebaut; im NFSU2-Projekt bewährt;
  rekursiver Descent + Lifter + Diff-Test in einem Werkzeugkasten; bringt die
  32-Bit-Laufzeiten (`recomp32`, `native32`) mit.
- **Alternativen verworfen:** Ghidra-Decompiler-Output (nicht kompilierbar, keine
  Laufzeit), manuelles Portieren (nicht skalierbar), x64-Lift (Architektur-Sprung,
  nicht Ziel).

## E2 — Ziel bleibt x86-32 (kein x64)

- **Kontext:** Frühere Überlegung war x64.
- **Entscheidung:** x86-32 → x86-32.
- **Begründung:** Kein Zeigerumbau, keine ABI-Anpassung; kleinster, verifizierbarer
  erster Schritt. Der x64-Schritt folgt später.

## E3 — `.securom` und die Nullsektion werden ausgeschlossen

- **Kontext:** `.securom` ist verschlüsselter DRM-Stub (Entropie 7.16); Sektion Nr. 10
  sind 17 MB Nullen (Entropie ~0.74).
- **Entscheidung:** Beide nicht liften; in Ghidra als Daten markieren.
- **Begründung:** Kein Spielcode; Liften produziert nur Müll.
- **Wirksam bei pcrecomp:** **nicht** automatisch. `disasm32` scannt jede Sektion mit
  `characteristics & 0x20000020` linear als Code — `.securom` (CODE) und `.data2` (EXEC)
  werden also mitgescannt. Die Begrenzung erfolgt über einen PE-Flag-Patch (siehe E9),
  nicht über die rekursive Erreichbarkeit.

## E4 — `.data2` (Sektion Nr. 8) NICHT blind löschen

- **Kontext:** Sektion ist als Daten mit EXECUTE-Flag markiert; Ghidra fand dort ~1.726
  „Funktionen".
- **Entscheidung:** Behalten.
- **Begründung:** Bei `0xE80000` liegen echte Code-Bytes; `0xE00000` wird als Daten
  referenziert. Das EXECUTE-Flag erzeugt Falsch-Funktionen — aber nicht ausschließlich.

## E5 — Ghidra-Bereinigung ist nur Referenz, nicht pcrecomp-Input

- **Kontext:** Der Auftrag nennt „Phase 1: Ghidra bereinigen" vor dem Lift.
- **Entscheidung:** Sauberer C-Export bleibt Referenz; pcrecomp bekommt **nicht** das
  Ghidra-Projekt, sondern eine **Kopie der EXE mit gepatchten Section-Flags** (E9).
- **Begründung:** pcrecomp disassembliert die EXE selbst; das Ghidra-Projekt beeinflusst
  den Lift nicht. Eine reine Flag-Änderung an der Sektionskopie ist der minimale,
  pcrecomp-eigene Mechanismus, um Nicht-Code-Bereiche auszuschließen.

## E9 — Nicht-Code-Sektionen per PE-Flag-Patch ausschließen

- **Kontext:** `disasm32` (pcrecomp) verwendet `is_code = characteristics & 0x20000020`.
  `.securom` trägt `CODE|EXEC`, `.data2` `IDATA|EXEC`. Beide werden dadurch als Code
  linear gescannt; in `.data2` entstehen Pseudo-Funktionen, die den Lauf zum Erliegen
  bringen (11,9 GB RAM, kein Fortschritt).
- **Entscheidung:** `scripts/patch_sections.py` erzeugt `build/Juiced.pcrecomp.exe` und
  löscht in den Section-Headern die Flags `CNT_CODE (0x20)` und `MEM_EXECUTE (0x20000000)`
  für `.securom` und `.data`. Bytes, Größen, Adressen bleiben unverändert.
- **Begründung:** Minimal-invasiv; pcrecomp überspringt die Bereiche dann sauber. Der
  Original-`Juiced.exe` bleibt unangetastet.
- **Alternativen verworfen:** `disasm32`-Code patchen (Fork, Upstream-Drift); Scan-Span
  per Hand verkleinern (keine CLI-Option, `.SCY` am Ende spannt ohnehin weit);
  `.data2` mitliften (RAM-Explosion). Echter Code in `.data2` kann später gezielt per
  `--seed-functions` nachgezogen werden.

## E6 — Runtime `native32`

> **Überholt durch E15.** `native32` ist MSVC-x86-only (`#error` in `native32.c`) und unter
> MinGW nicht baubar. Umgesetzt ist `recomp32` + `image_loader`. E6 bleibt als ursprüngliche
> Erwägung dokumentiert.

- **Kontext:** Juiced importiert KERNEL32/USER32/D3D9/DSOUND/DINPUT8/WS2_32/OLE32/BINKW32.
- **Entscheidung:** `recomp32` + `native32`.
- **Begründung:** `native32` leitet Importe an echtes Windows weiter → **keine DLL-Stubs**
  nötig.
- **Restrisiko:** BinkW32 muss als 32-Bit-DLL vorhanden sein, sonst kein Video.

## E7 — Doku + Reproduktion sind Pflichtbestandteil jedes Schritts

- **Kontext:** Neue Anforderung.
- **Entscheidung:** Jeder Schritt schreibt `logs/<schritt>.log` und wird in
  `docs/reproduktion.md` (Ziel/Voraussetzungen/Befehl/Erwartet/Tatsächlich/Abweichung)
  festgehalten. Commits enthalten die Doku.
- **Definition of Done:** Schritt gilt erst als fertig, wenn Doku + Log vorliegen.

## E8 — Logs sind generierte Artefakte (nicht versioniert)

- **Kontext:** `.gitignore` schließt `*.log` aus.
- **Entscheidung:** `logs/` wird per `reproduce` erzeugt und **nicht** committet
  (nur `logs/.gitkeep`). Die inhaltlichen Ergebnisse stehen in `docs/reproduktion.md`.
- **Begründung:** Logs sind reproduzierbar und teils groß; Doku bleibt die Quelle der Wahrheit.

## E10 — pcrecomp-`difftest`-x87-Fehler sind ein GCC-Link-Artefakt

- **Kontext:** difftest meldete 273/368 mit 95 x87-Fehlern (geliftete GPRs = 0), obwohl
  der Lift selbst fehlerfrei ist.
- **Befund:** Im GCC-Pfad legt der Linker das im Header **weak** definierte, null-initialisierte
  Schattenarray `g_st_i64[8]` (`RECOMP_SHARED_DATA`) überlappend auf die Registerglobals; jeder
  `fp_push`/`fp_pop` überschreibt dadurch `eax/ecx/edx/esp/ebx`.
- **Entscheidung:** Als **Umgebungsartefakt** dokumentieren **und** per reproduzierbarem
  Patch beheben: `scripts/patch_recomp_weak.py` verschiebt die weak-Definition in eine
  explizite Sektion (`__attribute__((weak, section(".data")))`). `weak` bleibt erhalten →
  weiterhin genau eine geteilte Instanz über mehrere Übersetzungseinheiten (MSVC unberührt).
- **Verifikation:** Mit dem Patch **368/368, 0 Fehler**; ein Zwei-TU-Test linkt ohne
  Duplikat-Fehler und teilt `g_st_i64`. Der pcrecomp-Klon bleibt commit-gepinnt (`d1319ed`);
  der Fix ist ein separater, idempotenter Schritt (`scripts/reproduce.*`, Schritt 5).
- **Begründung:** MSVC nutzt `__declspec(selectany)`; GNU ld reserviert bei einer
  null-initialisierten weak-.bss-Definition (COFF) keinen Platz und legt sie überlappend ab.
  GCC-spezifisch und für den späteren MinGW-Build (FPU-lastige Funktionen) relevant, aber
  kein Lift- und kein Juiced-Problem.

## E11 — 32-Bit-Build mit MSYS2-MinGW + Smoke-Link statt Vollbau

- **Kontext:** Für Phase 3 fehlte ein 32-Bit-Compiler (Juiced ist i386; der vorhandene
  ucrt64-gcc ist 64-Bit). Ziel war ein erster, lauffähiger 32-Bit-PoC.
- **Entscheidung (Toolchain):** MSYS2-Repo `mingw32` per pacman:
  `mingw-w64-i686-gcc` 16.2.0, `-cmake` 4.4.4, `-ninja` 1.13.2. Kein MSVC/Clang nötig.
- **Entscheidung (PoC-Umfang):** `scripts/build_poc.cmd` linkt die Runtime + **eine**
  geliftete TU (`recomp_0000.c`) zu `build\juiced_poc.exe` (machine 0x014C, 32-bit).
  Ergebnis: 14,36 MB, läuft, `sizeof(void*)=4`.
- **Fehlende Symbole:** `--unresolved-symbols=ignore-all` wird vom mingw-ld im PE-Pfad nicht
  honoriert; die `sub_*` der nicht gelinkten TUs werden über generierte **weak-Leer-Stubs**
  (`scripts/gen_weak_stubs.py`) geschlossen. Starke Definitionen überschreiben die Stubs,
  sobald die jeweilige TU im Vollbau mitgelinkt wird — kein Verhalten wird vorgetäuscht.
- **Vollbau:** `poc\CMakeLists.txt` skelettiert den Link **aller** 120 TUs (~772 MB C),
  noch **nicht** ausgeführt (Zeit/RAM, 32-Bit-`ld`-Limit). Der PoC belegt die Toolchain,
  nicht die Lauffähigkeit des Spiels.
- **Begründung:** Schnellster Nachweis, dass Compiler + Runtime-Fix + gelifteter Code sich zu
  einem 32-Bit-PE linken lassen, ohne den teuren Vollbau vorzuziehen.

## E12 — Vollbau aller 120 TUs + Behebung dreier Build-Blocker

- **Kontext:** Nach dem Smoke-Link (E11) sollte der Link **aller** 120 gelifteten TUs belegt
  werden. Dabei traten drei reproduzierbare Blocker auf.
- **Entscheidungen / Fixes (alle per Skript, idempotent):**
  1. **`cc1 out of memory`** (größte TUs 37 MB): 32-Bit-`cc1` ohne LAA auf ~2 GB begrenzt →
     `scripts/patch_cc1_laa.py` setzt das LARGE_ADDRESS_AWARE-Bit (`cc1`/`cc1plus`; `ld` hat es
     bereits) und es werden `--param ggc-min-heapsize=32768 ggc-min-expand=10` verwendet.
     Kein Wechsel auf clang (die ucrt64-clang-Pakete sind auf diesem System nicht lauffähig:
     `STATUS_ENTRYPOINT_NOT_FOUND`).
  2. **`label 'L_…' used but not defined`** (15 Dateien / 37 Labels): Lift-Defekt für Sprungziele
     aus dem linearen Over-Scan → `scripts/patch_undefined_labels.py` ergänzt die fehlende
     Label-Definition am Funktionsanfang (nur Garbage-/Dead-Code).
  3. **Undefinierte `sub_*`** (20.697 von den TUs **referenziert**, davon **17.124 nirgends
     definiert** = „schwarze Löcher"): Ziele außerhalb von Katalog/Image → `scripts/gen_link_stubs.py`
     erzeugt weak-Leer-Stubs; die vollständige Liste liegt in `logs/link_stubs.txt`. Stubs
     müssen **nach** dem Kompilieren erzeugt werden (nm über die Objekte).
     Zusätzlich `-Wno-error=implicit-function-declaration` (gcc 14+ stufte das zum Fehler hoch).
- **Ergebnis:** `scripts/build_full.cmd` → **`build\juiced_full.exe`, 376,1 MB, machine 0x014C
  (i386), läuft**. Verbleibende obige Punkte sind Werkzeug-/Lift-Randfälle in nicht erreichbarem
  Code, nicht Teil der verifizierten Logik.
- **Grenze:** Der Vollbau beweist Übersetz-/Linkbarkeit als 32-Bit-PE, **nicht** die
  Lauffähigkeit des Spiels (Smoke-`main`, kein Speicher-Layout/Imports/DRM).
- **Begründung:** Alle drei Blocker sind umgebungs- bzw. randcodebedingt und per Skript
  behebbar; die Abweichung zu pcrecomp bleibt als umgebungsnahe Dokumentation sichtbar.

## E13 — Build über Ninja (parallel + inkrementell) mit ccache

- **Kontext:** Der erste Vollbau lief sequenziell (~40 min) und war für Iterationen untauglich;
  Ziel waren < 15 min (Voll) bzw. < 2 min (inkrementell).
- **Entscheidung:** Die `for`-Schleife in `build_full.cmd` wird durch einen **Ninja**-Build
  ersetzt. `scripts/gen_build_ninja.py` erzeugt `build\build.ninja`:
  Regel `cc` (Präfix **ccache**, falls vorhanden) + `link` + `stubs` (erzeugt
  `link_stubs.c` per `nm` über die Objekte **nach** dem Kompilieren). Explizite Header-Deps
  (`recomp_funcs.h`, `recomp_types.h`) sichern korrekte Inkrementalität. State via `builddir = build`
  (ersatzweise gitignored `.ninja_log`/`.ninja_deps`).
- **Ergebnis:** Kalt-Vollbau **12,9 min** (Ziel < 15 ✔); inkrementell **2,9 min** (Ziel < 2 ✘).
- **Grenze / Begründung:** Der **Single-Thread-GNU-`ld`**-Link (~165 s, unabhängig von
  `--gc-sections`: 166/168 s) dominiert den inkrementellen Fall; ccache hilft nur beim
  Kompilieren. **`lld`** würde das lösen, ist auf diesem System aber nicht lauffähig
  (`ucrt64-lld` → `0xC0000139`; kein i686-`lld`-Paket). Workaround: einzelne Objekte bauen
  (`ninja … build/full/recomp_XXXX.o`).
- **Offen:** Falls ein funktionierendes 32-Bit-`lld` verfügbar wird, nur die Link-Regel
  (`ld.lld`/`-fuse-ld=lld`) in `gen_build_ninja.py` umstellen → Inkrementell-Ziel erreichbar.

## E14 — Ein-Funktions-Difftest gegen echten Juiced-Code (Phase 3.4)

- **Kontext:** Der pcrecomp-`difftest` prüft nur einen festen Instruktions-Corpus (Lifter-PoC).
  Der Auftrag verlangt einen PoC an einer **echten** Juiced-Funktion.
- **Entscheidung:** `scripts/difftest_fn.py` setzt auf die difftest-Engine auf, zieht die
  Funktionsbytes aber aus `build\Juiced.pcrecomp.exe` (per `juiced_functions.json`) und wählt
  mit `scripts/find_leaf.py` geeignete Blattfunktionen. Vergleich: geliftetes C vs. Unicorn
  (acht GPRs, definierte EFLAGS, Gast-Speicher).
- **Kerndetails:**
  1. Funktion läuft im difftest-Fenster bei `BASE` (0x400000); Lift-Ausgabe ist rein relativ.
  2. Das abschließende `ret` wird abgeschnitten, damit Unicorn am Funktionsende hält und beide
     Seiten **vor** dem Rücksprung vergleichen; sein Adress-Label bleibt stehen, damit jcc
     dorthin als `goto` landen.
  3. `lift32` ruft für Sprünge `insn.get_branch_target()` — nur `disasm32.Instruction` hat das.
     Ein dünner Shim ergänzt die eine Methode auf capstone-Insns; Labels an jeder Adresse
     (`label_all`, wie `generate.py` bei indirekten Sprüngen) machen interne jcc zu `goto`.
- **Ergebnis:** Register-only, Speicher-lesende (stdcall-Frame) und verzweigende Blätter
  stimmen bit-genau (`0x0049C682`, `0x0062D21B`, `0x00C52BF8` in beiden Pfaden).
- **Grenzen / offen:** Absolute Speicheroperanden brauchen Image-Mapping an Original-VAs;
  eingebettete `ret` (früher Rücksprung) werden derzeit abgelehnt. Beides ist die nächste
  Ausbaustufe (echtes Speicher-Layout + Runtime-`main`).

## E15 — Runtime lädt das echte Image, Host wird hoch gelinkt (Phase 3.1)

- **Kontext:** Phase 3.1 soll gelifteten Code gegen den **echten Programmstart-Speicher**
  ausführen. `native32` (Auftrags-Empfehlung) ist unter MinGW nicht baubar (MSVC-x86-only,
  `#error` in `native32.c`), `win32hle` zielt auf SDL2/POSIX. Übrig bleibt `recomp32` + der
  mitgelieferte generische PE-Loader `image_loader.c`.
- **Entscheidung:** Ein eigener `poc\runtime_main.c` mappt `Juiced.exe` über
  `recomp_load_image` ins Adressfenster des Prozesses, richtet einen Stack ein und ruft
  geliftete Funktionen auf.
- **Kerndetails:**
  1. **Host-Base:** `build\juiced_run.exe` wird mit `-Wl,--image-base,0x10000000` gelinkt
     (Ninja-Regel `linkrun`). Sonst würde MinGWs Default-Base `0x400000` mit der Ziel-VA
     kollidieren.
  2. **Rebase statt Fix-Base:** `0x00400000` kann durch DLL-ASLR belegt sein
     (`VirtualAlloc` fixed schlägt fehl). Die Runtime probiert mehrere Basen und setzt
     `g_mem_base = base - 0x400000`; der Lift rechnet jede Gast-VA über
     `ADDR(va)=va+g_mem_base` — genau der Zweck des Feldes.
  3. **Diagnose:** VEH-Handler protokolliert AV-Ziel, `g_cur_func`, Register und ICALL-Ringpuffer;
     `recomp_lookup_import` liefert bewusst `NULL`, damit unaufgelöste Importe **geloggt**
     statt blind gesprungen werden.
  4. **Stack + TIB als Gast-VAs:** Auch `esp` und `fs:` laufen über `ADDR`, deshalb ist `g_esp`
     `HOST2GUEST(stack_top)` und `g_fs_base` zeigt auf eine simulierte TIB
     (`0x01030000`, `fs:[0]=0xFFFFFFFF`, StackBase/Limit, Self). Ohne das schreibt der SEH-Prolog
     `fs:[0]` nach `ADDR(0)` (unmapped).
  5. `recomp_dispatch.o` muss als eigene TU gelinkt werden (der Glob `recomp_[0-9]*.c` schließt
     `recomp_dispatch.c` aus).
  6. `scripts\iat_names.py` löst IAT-Slots/gebundene Adressen über die Import-Tabelle in
     `DLL!Funktion` auf.
- **Ergebnis:** Blattfunktionen mit absoluten Global-Zugriffen laufen korrekt gegen die echten
  Image-Daten (`mov [0x76A090],eax`; `fld dword [0x7019A8]` → 1.38). Der EP 0x005CD316 läuft durch
  den SEH-Prolog und erreicht die ersten echten Importe: `kernel32!GetVersionExA` (Slot
  `0x6CC1EC`, gebunden `0x7C812B6E`) und `kernel32!GetModuleHandleA` (Slot `0x6CC168`, gebunden
  `0x7C80B731`). Danach folgt ein `ADDR(0)`-Zugriff, weil ein aufgelöster Import `NULL` liefert
  und als Zeiger genutzt wird.
- **Offen:** Import-Bridge (IAT-Slots auf Host-Funktionen/Stubs mit bekanntem stdcall-`argc`
  umbiegen); danach EP weiterlaufen lassen und die Importfolge protokollieren.
