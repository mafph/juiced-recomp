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
- **Wirksam bei pcrecomp:** automatisch, weil `disasm32` rekursiv vom Entry/Exports läuft
  und diese Bereiche nicht erreicht.

## E4 — `.data2` (Sektion Nr. 8) NICHT blind löschen

- **Kontext:** Sektion ist als Daten mit EXECUTE-Flag markiert; Ghidra fand dort ~1.726
  „Funktionen".
- **Entscheidung:** Behalten.
- **Begründung:** Bei `0xE80000` liegen echte Code-Bytes; `0xE00000` wird als Daten
  referenziert. Das EXECUTE-Flag erzeugt Falsch-Funktionen — aber nicht ausschließlich.

## E5 — Ghidra-Bereinigung ist nur Referenz, nicht pcrecomp-Input

- **Kontext:** Der Auftrag nennt „Phase 1: Ghidra bereinigen" vor dem Lift.
- **Entscheidung:** Sauberer C-Export bleibt Referenz; pcrecomp bekommt die **unveränderte**
  EXE.
- **Begründung:** pcrecomp disassembliert die EXE selbst; das Ghidra-Projekt beeinflusst
  den Lift nicht.

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
