"""
find_leaf.py - geeignete Blattfunktionen fuer den Ein-Funktions-Difftest finden.

Kriterien (konservativ, fuer den ersten Harness):
  * calls_to leer, entry_kind == "start"
  * kleine Groesse
  * nur "einfache" Instruktionen (kein call/jmp externe, keine FPU/SSE,
    keine String-Ops, kein rep)
  * Speicheroperanden hoechstens [esp+N]/[ebp+N] (keine absoluten Adressen),
    damit der erste Vergleich nur Register+Stack braucht

Aufruf:  python scripts/find_leaf.py [--n 12]
"""
import json
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import pefile

CAT = "juiced_functions.json"
EXE = "build/Juiced.pcrecomp.exe"

SAFE_MNEMONICS = {
    "mov", "movzx", "movsx", "lea", "add", "sub", "xor", "and", "or", "not",
    "neg", "inc", "dec", "imul", "mul", "shl", "shr", "sar", "rol", "ror",
    "test", "cmp", "push", "pop", "nop", "ret", "cdq", "cwde",
    "sete", "setne", "setl", "setle", "setg", "setge", "seta", "setae",
    "setb", "setbe", "sets", "setns", "seto", "setno", "setp", "setnp",
    "jmp", "je", "jne", "jl", "jle", "jg", "jge", "ja", "jae", "jb", "jbe",
    "js", "jns", "jo", "jno", "jp", "jnp",
}
JCC = ("j",)


def main():
    n = 12
    lo, hi = 10, 40
    if "--n" in sys.argv:
        n = int(sys.argv[sys.argv.index("--n") + 1])
    if "--min" in sys.argv:
        lo = int(sys.argv[sys.argv.index("--min") + 1])
    if "--max" in sys.argv:
        hi = int(sys.argv[sys.argv.index("--max") + 1])
    interesting = "--interesting" in sys.argv
    INTERESTING = ("imul", "mul", "div", "idiv", "cdq", "cwde")

    pe = pefile.PE(EXE, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    raw = open(EXE, "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True

    data = json.load(open(CAT))
    out = []
    for f in data["functions"]:
        if f["calls_to"] or f["entry_kind"] != "start":
            continue
        size = f["size"]
        if not (lo <= size <= hi):
            continue
        try:
            off = pe.get_offset_from_rva(f["address"] - base)
        except Exception:
            continue
        code = raw[off:off + size]
        insns = list(md.disasm(code, f["address"]))
        if not insns or insns[-1].mnemonic != "ret":
            continue
        ok = True
        for ins in insns:
            m = ins.mnemonic
            if m not in SAFE_MNEMONICS or m == "jmp":
                ok = False
                break
            for op in ins.operands:
                if op.type == 3:  # X86_OP_MEM
                    if op.mem.base == 0 and op.mem.index == 0 and op.mem.disp != 0:
                        ok = False  # absolute address -> braucht Daten-Mapping
                        break
            if not ok:
                break
        if ok:
            # alle Sprungziele muessen in der Funktion liegen (sonst Loop-Rumpf)
            end = f["address"] + size
            for ins in insns:
                if ins.mnemonic.startswith("j") and ins.mnemonic != "jmp":
                    tgt = ins.address + ins.size + ins.operands[0].imm
                    if not (f["address"] <= tgt < end):
                        ok = False
                        break
        if ok:
            if interesting:
                mns = [i.mnemonic for i in insns]
                if not (any(m in INTERESTING for m in mns) or
                        any(m.startswith("j") and m != "jmp" for m in mns)):
                    continue
            out.append((size, f["address_hex"], f["name"], insns))

    out.sort(key=lambda t: t[0])
    for size, va, name, insns in out[:n]:
        print("=== %s  %s  (%d B) ===" % (va, name, size))
        for ins in insns:
            print("   %s %s" % (ins.mnemonic, ins.op_str))
    print("\n%d Kandidaten gefunden." % len(out))


if __name__ == "__main__":
    main()
