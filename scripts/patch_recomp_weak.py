"""
patch_recomp_weak.py - behebt die MinGW/GCC-Layout-Kollision der pcrecomp-Runtime.

Im GCC-Zweig definiert `runtime/recomp32/recomp_types.h` das null-initialisierte
Schattenarray `g_st_i64[8]` als `__attribute__((weak))`. GNU ld legt eine solche
weak-.bss-Definition im COFF-Format ohne reservierte Groesse ab und ueberlappt sie
mit den Registerglobals `g_eax/g_ecx/g_edx/g_esp/g_ebx`; jeder `fp_push`/`fp_pop`
ueberschreibt dadurch diese GPRs. Sichtbar wird das in `tools/lift/difftest.py`:
273/368 statt 368/368 (95 x87-Faelle mit gelifteten GPRs = 0).

Fix: die weak-Definition in eine explizite Sektion legen, damit der Linker den
Platz korrekt reserviert. `weak` bleibt erhalten -> weiterhin genau eine geteilte
Instanz ueber mehrere Uebersetzungseinheiten (MSVC nutzt selectany, unberuehrt).

Aufruf:
    python scripts/patch_recomp_weak.py [pfad/zu/recomp_types.h]

Idempotent: bereits gepatchte Datei bleibt unveraendert.
"""
import sys
import os

TARGET_DEFAULT = os.path.join("pcrecomp", "runtime", "recomp32", "recomp_types.h")
OLD = '#define RECOMP_SHARED_DATA __attribute__((weak))'
NEW = '#define RECOMP_SHARED_DATA __attribute__((weak, section(".data")))'


def patch(path):
    if not os.path.isfile(path):
        raise SystemExit(f"nicht gefunden: {path}")

    with open(path, "r", encoding="utf-8", newline="") as f:
        text = f.read()

    if NEW in text:
        print(f"  bereits gepatcht: {path}")
        return
    if OLD not in text:
        raise SystemExit(f"  Muster nicht gefunden in {path} (pcrecomp-Version geprueft?)")

    text = text.replace(OLD, NEW, 1)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(f"  gepatcht: {path}")
    print(f"    {OLD}")
    print(f"    -> {NEW}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else TARGET_DEFAULT
    patch(target)
