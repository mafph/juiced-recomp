"""
gen_link_stubs.py - sammelt alle undefinierten `sub_*`-Symbole aus einer Menge
kompilierter Objekte (via nm -u) und erzeugt daraus eine C-Datei mit weak-Leer-Stubs.

Zweck: Der geliftete Code ruft vereinzelt Ziele auf, die nicht im Funktionskatalog
stehen (z. B. aus dem linearen Over-Scan stammende Adressen ausserhalb des Images,
etwa ``sub_ED284540``). Sie sind weder deklariert noch in irgendeiner TU definiert
und wuerden den Link abbrechen. weak-Stubs schliessen genau diese Luecken; echte
Definitionen (stark) gewinnen stets.

Aufruf:
    python scripts/gen_link_stubs.py <obj_dir> <out.c> [nm_pfad]
"""
import glob
import os
import re
import subprocess
import sys

DEF_NM = r"C:\msys64\mingw32\bin\nm.exe"
UNDEF = re.compile(r"^\s*U\s+_?(sub_[0-9A-Fa-f]+)\s*$")


def main():
    if len(sys.argv) < 3:
        raise SystemExit("Aufruf: gen_link_stubs.py <obj_dir> <out.c> [nm]")
    obj_dir, out = sys.argv[1], sys.argv[2]
    nm = sys.argv[3] if len(sys.argv) > 3 else DEF_NM

    names = set()
    objs = glob.glob(os.path.join(obj_dir, "*.o"))
    for i, o in enumerate(objs, 1):
        r = subprocess.run([nm, "-u", o], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            m = UNDEF.match(line)
            if m:
                names.add(m.group(1))
        if i % 20 == 0:
            print("  ... %d/%d Objekte" % (i, len(objs)))

    names = sorted(names)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("/* auto-generated weak link stubs */\n")
        for n in names:
            f.write(f"__attribute__((weak)) void {n}(void) {{}}\n")
    print("%d undefinierte sub_*-Symbole -> %s" % (len(names), out))


if __name__ == "__main__":
    main()
