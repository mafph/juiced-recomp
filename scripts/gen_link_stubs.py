"""
gen_link_stubs.py - sammelt alle undefinierten `sub_*`-Symbole aus einer Menge
kompilierter Objekte (via nm -u) und erzeugt daraus eine C-Datei mit weak-Leer-Stubs.

Zweck: Der geliftete Code ruft vereinzelt Ziele auf, die nicht im Funktionskatalog
stehen (z. B. aus dem linearen Over-Scan stammende Adressen ausserhalb des Images,
etwa ``sub_ED284540``). Sie sind weder deklariert noch in irgendeiner TU definiert
und wuerden den Link abbrechen. weak-Stubs schliessen genau diese Luecken; echte
Definitionen (stark) gewinnen stets.

Die Liste der so geschlossenen Symbole wird zusaetzlich als Klartext protokolliert
(Default logs/link_stubs.txt): Das sind die "schwarzen Loecher" des Rohlings -- sie
werden aufgerufen, liefern aber Muelle. Spaeter muss man wissen, welche das sind.

Aufruf:
    python scripts/gen_link_stubs.py <obj_dir> <out.c> [nm_pfad] [log.txt]
"""
import datetime
import glob
import os
import re
import subprocess
import sys

DEF_NM = r"C:\msys64\mingw32\bin\nm.exe"
DEF_LOG = os.path.join("logs", "link_stubs.txt")
UNDEF = re.compile(r"^\s*U\s+_?(sub_[0-9A-Fa-f]+)\s*$")
DEF = re.compile(r"^\s*[0-9A-Fa-f]+\s+[A-Za-z]\s+_?(sub_[0-9A-Fa-f]+)\s*$")


def main():
    if len(sys.argv) < 3:
        raise SystemExit("Aufruf: gen_link_stubs.py <obj_dir> <out.c> [nm] [log]")
    obj_dir, out = sys.argv[1], sys.argv[2]
    nm = sys.argv[3] if len(sys.argv) > 3 else DEF_NM
    log_path = sys.argv[4] if len(sys.argv) > 4 else DEF_LOG

    undefined = set()
    defined = set()
    objs = glob.glob(os.path.join(obj_dir, "*.o"))
    for i, o in enumerate(objs, 1):
        r = subprocess.run([nm, o], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            m = UNDEF.match(line)
            if m:
                undefined.add(m.group(1))
                continue
            m = DEF.match(line)
            if m:
                defined.add(m.group(1))
        if i % 20 == 0:
            print("  ... %d/%d Objekte" % (i, len(objs)))

    # Echte "schwarze Loecher": aufgerufen, aber in KEINEM Objekt definiert.
    holes = sorted(undefined - defined)

    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("/* auto-generated weak link stubs */\n")
        for n in holes:
            f.write(f"__attribute__((weak)) void {n}(void) {{}}\n")

    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    with open(log_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# undefinierte sub_*-Symbole (weak-Leer-Stubs; Rohling-Schwarze-Loecher)\n")
        f.write("# Stand: %s\n" % datetime.datetime.now().isoformat(timespec="seconds"))
        f.write("# Quellobjekte: %s (*.o)\n" % obj_dir)
        f.write("# referenziert+undefiniert: %d, davon nirgends definiert (Luecken): %d\n"
                % (len(undefined), len(holes)))
        for n in holes:
            f.write(n + "\n")

    print("%d Luecken (von %d referenzierten) -> %s (Liste: %s)"
          % (len(holes), len(undefined), out, log_path))


if __name__ == "__main__":
    main()
