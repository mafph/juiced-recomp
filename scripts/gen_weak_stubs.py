"""
gen_weak_stubs.py - erzeugt weak-Leer-Stubs fuer alle in recomp_funcs.h deklarierten
Funktionen.

Zweck: Smoke-Link EINER gelifteten TU (Phase-3-PoC). Beim Verlinken nur eines
recomp_*.o fehlen die sub_*-Definitionen der uebrigen TUs. Diese weak-Stubs
schliessen die Luecke, ohne echtes Verhalten vorzutaeuschen: sobald die jeweilige
TU mitgelinkt wird, gewinnt ihre starke Definition den Stub.

Aufruf:
    python scripts/gen_weak_stubs.py juiced_lifted/recomp_funcs.h build/poc_stubs.c
"""
import re
import sys


def main():
    if len(sys.argv) < 3:
        raise SystemExit("Aufruf: gen_weak_stubs.py <recomp_funcs.h> <out.c>")
    src, dst = sys.argv[1], sys.argv[2]

    with open(src, "r", encoding="utf-8") as f:
        names = re.findall(r"^void\s+(\w+)\(void\);", f.read(), re.M)

    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write("/* auto-generated weak stubs - nur fuer den Smoke-Link */\n")
        for n in names:
            f.write(f"__attribute__((weak)) void {n}(void) {{}}\n")
    print(f"{len(names)} weak stubs -> {dst}")


if __name__ == "__main__":
    main()
