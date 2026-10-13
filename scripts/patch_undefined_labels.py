"""
patch_undefined_labels.py - behebt Lift-Defekte des Translators, bei denen ein
Sprungziel-Label benutzt, aber nie definiert wird ("label 'L_...' used but not
defined"). Ursache sind Adressen aus dem linearen Over-Scan (teils ausserhalb des
Images), deren Label der Translator nicht emittiert hat.

Fix: pro betroffener Funktion wird die fehlende Label-Definition (leere Anweisung)
direkt nach der oeffnenden Klammer eingefuegt. Das betrifft ausschliesslich
Garbage-/Dead-Code; fuer den Link-PoC genuegt die Uebersetzbarkeit.

Idempotent. Aufruf:
    python scripts/patch_undefined_labels.py [juiced_lifted]
"""
import glob
import os
import re
import sys

FUNC = re.compile(r"^void\s+sub_[0-9A-Fa-f]+\(void\)\s*\{")
GOTO = re.compile(r"\bgoto\s+(L_[0-9A-Fa-f]+)\s*;")
DEF = re.compile(r"^\s*(L_[0-9A-Fa-f]+)\s*:", re.M)


def patch_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    defined = set(DEF.findall("".join(lines)))

    funcs = {}  # index of function-opening line -> set of missing labels used inside
    cur = None
    for i, ln in enumerate(lines):
        if FUNC.match(ln):
            cur = i
        for lab in GOTO.findall(ln):
            if lab not in defined:
                funcs.setdefault(cur, set()).add(lab)
    if not funcs:
        return 0

    out = []
    added = 0
    for i, ln in enumerate(lines):
        out.append(ln)
        if i in funcs:
            for lab in sorted(funcs[i]):
                out.append(f"{lab}: ; /* auto-patch: undefiniertes Sprungziel */\n")
                added += 1
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("".join(out))
    return added


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "juiced_lifted"
    files = sorted(glob.glob(os.path.join(root, "recomp_[0-9]*.c")))
    total = 0
    touched = 0
    for p in files:
        n = patch_file(p)
        if n:
            touched += 1
            total += n
            print("  %s: +%d Labels" % (os.path.basename(p), n))
    print("Dateien angepasst: %d, Labels ergaenzt: %d" % (touched, total))


if __name__ == "__main__":
    main()
