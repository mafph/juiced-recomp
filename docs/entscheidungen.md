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
- **Entscheidung:** Als **Umgebungsartefakt** dokumentieren. Der pcrecomp-Klon bleibt unverändert
  (kein dauerhafter Patch), bis ein 32-Bit-/MSVC-Pfad feststeht. Ohne `weak` (Test) sind 368/368
  grün — nachgewiesen.
- **Begründung:** MSVC nutzt `__declspec(selectany)`; die Kollision ist GCC-spezifisch und für
  den späteren MinGW-Build relevant, aber kein Lift- und kein Juiced-Problem.

