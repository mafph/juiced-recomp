"""
difftest_fn.py - Ein-Funktions-Difftest: geliftetes C vs. Unicorn (echter Juiced-Code).

Wiederverwendet die Engine aus pcrecomp/tools/lift/difftest.py (Lifter + Vergleich),
aber statt eines festen Instruktions-Corpus wird eine echte Funktion aus
Juiced.pcrecomp.exe genommen (Bytes aus dem pcrecomp-Funktionskatalog).

Der Code laeuft im difftest-Gastfenster bei BASE=0x400000 (0x400000..0x440000).
Die Lift-Ausgabe ist rein relativ, also an jeder Adresse lauffaehig; absolute
Speicheroperanden werden abgelehnt (die brauchen ein echtes Image-Mapping, die
zweite Ausbaustufe). Stack/Argumente/Objekte muessen im Fenster liegen.

--frame, --arg, --this richten den ueblichen Aufruf ein:
    ebp=F, esp=F+4, [F]=Rueckkehradresse, [F+8+4i]=Argumente, ecx=this.

Der abschliessende `ret` wird abgeschnitten, damit beide Maschinen VOR dem
Ruecksprung vergleichen (Unicorn springt sonst zur Rueckkehradresse).

Aufruf:
    python scripts/difftest_fn.py 0x0049C682 --reg edx=0x12345678
    python scripts/difftest_fn.py 0x0062D21B --frame 0x412000 --this 0x411000 \
        --arg 0x411000 --mem 0x411042=1000 --mem 0x4110a4=04030201
"""
import argparse
import json
import os
import shutil
import sys
import tempfile

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import pefile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PCRE = os.path.join(ROOT, "pcrecomp")
sys.path.insert(0, PCRE)

from tools.lift import difftest as dt  # noqa: E402
from capstone.x86 import X86_OP_IMM  # noqa: E402


class _InsnShim:
    """capstone-Insn mit der einzigen Zusatzmethode, die der Lifter braucht.

    lift32._lift_instruction ruft fuer Spruenge insn.get_branch_target(); das
    existiert nur auf disasm32.Instruction, nicht auf capstone. Alles andere
    (address, bytes, mnemonic, op_str, operands, size) delegiert der Shim.
    """
    def __init__(self, ins):
        self._i = ins

    def __getattr__(self, name):
        return getattr(self._i, name)

    def get_branch_target(self):
        if self._i.operands:
            op = self._i.operands[0]
            if op.type == X86_OP_IMM:
                return op.imm & 0xFFFFFFFF
        return None


CAT = os.path.join(ROOT, "juiced_functions.json")
EXE = os.path.join(ROOT, "build", "Juiced.pcrecomp.exe")


def load_fn(va):
    cat = json.load(open(CAT))
    for f in cat["functions"]:
        if f["address"] == va:
            return f
    raise SystemExit("Funktion 0x%08X nicht im Katalog" % va)


def bytes_at(va, size):
    pe = pefile.PE(EXE, fast_load=True)
    off = pe.get_offset_from_rva(va - pe.OPTIONAL_HEADER.ImageBase)
    return open(EXE, "rb").read()[off:off + size]


def _lift_case(case):
    """Wie difftest.lift_case, aber mit Shim, Labels und Branch-Unterstuetzung.

    Labels an jeder Instruktionsadresse (label_all, wie generate.py fuer
    indirekte Spruenge) und das abgeschnittene-ret-Label, damit jcc innerhalb
    der Funktion als `goto` landen statt als ITAIL.
    """
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    insns = list(md.disasm(bytes(case.code), dt.BASE))
    ret_addr = getattr(case, "_ret_addr", None)

    labels = {i.address for i in insns}
    if ret_addr is not None:
        labels.add(ret_addr)

    lifter = dt.Lifter(precise_carry=case.precise_carry)
    lifter._labels = labels
    lifter._jump_targets = set()
    lifter._flag_state = None

    body = []
    for insn in insns:
        body.append("L_%08X:" % insn.address)
        lifter._flag_state = None
        for line in lifter.lift_instruction(_InsnShim(insn)):
            body.append("    " + line)
    if ret_addr is not None:
        body.append("L_%08X: ;" % ret_addr)
    return body


dt.lift_case = _lift_case


def strip_trailing_ret(code, va):
    """Schneidet das abschliessende ret ab; liefert (code, insns, ret_addr).

    Eingebettete rets (fruehe Rueckspruenge) werden abgelehnt: die wuerden im
    gelifteten C mitten im Koerper `return;` erzeugen und die Flags-Auswertung
    ueberspringen. Das abschliessende ret wird entfernt, damit Unicorn am
    Funktionsende anhaelt und beide Maschinen VOR dem Ruecksprung vergleichen.
    """
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    insns = list(md.disasm(code, va))
    if not insns or not insns[-1].mnemonic.startswith("ret"):
        raise SystemExit("letzte Instruktion ist kein ret")
    for i in insns[:-1]:
        if i.mnemonic.startswith("ret"):
            raise SystemExit("Funktion hat ein eingebettetes ret "
                             "(0x%08X) - noch nicht unterstuetzt" % i.address)
    ret = insns[-1]
    return code[:ret.address - va], insns, ret.address


def has_absolute_mem(code, va):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    for ins in md.disasm(code, va):
        for op in ins.operands:
            if op.type == 3 and op.mem.base == 0 and op.mem.index == 0 and op.mem.disp != 0:
                return True
    return False


def in_window(addr, n=4):
    return dt.BASE <= addr and addr + n <= dt.BASE + dt.SIZE


def main():
    ap = argparse.ArgumentParser(description="Ein-Funktions-Difftest vs. Unicorn")
    ap.add_argument("va", help="Funktionsadresse, z.B. 0x0049C682")
    ap.add_argument("--reg", action="append", default=[],
                    help="Startregister, z.B. --reg edx=0x12345678 (mehrfach)")
    ap.add_argument("--mem", action="append", default=[],
                    help="Gast-Speicher, z.B. --mem 0x411014=01020304 (mehrfach)")
    ap.add_argument("--frame", help="EBP des Aufrufs -> esp=EBP+4, [EBP]=Rueckkehr")
    ap.add_argument("--ret", default=None, help="Rueckkehradresse [EBP] (Default BASE)")
    ap.add_argument("--arg", action="append", default=[],
                    help="StdCall-Argument (4 B, hex) ab [EBP+8], fortlaufend")
    ap.add_argument("--this", help="ecx setzen (thiscall)")
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    va = int(args.va, 16)
    f = load_fn(va)
    code = bytes_at(va, f["size"])
    code, insns, ret_addr = strip_trailing_ret(code, va)
    if has_absolute_mem(code, va):
        raise SystemExit("Funktion nutzt absolute Speicheroperanden - "
                         "braucht Image-Mapping (noch nicht unterstuetzt)")

    regs = {}
    for r in args.reg:
        name, val = r.split("=")
        regs[name.strip().lower()] = int(val, 16)

    mem = {}
    for m in args.mem:
        a, hexs = m.split("=")
        mem[int(a, 16)] = bytes.fromhex(hexs)

    if args.frame:
        ebp = int(args.frame, 16)
        ret = int(args.ret, 16) if args.ret else dt.BASE
        regs["ebp"] = ebp
        regs["esp"] = ebp + 4
        mem[ebp] = ret.to_bytes(4, "little")
        for i, v in enumerate(args.arg):
            mem[ebp + 8 + 4 * i] = int(v, 16).to_bytes(4, "little")
        if args.arg:
            regs.setdefault("eax", 0)

    if args.this:
        regs["ecx"] = int(args.this, 16)

    for a in list(mem):
        if not in_window(a, len(mem[a])):
            raise SystemExit("Speicher 0x%08X liegt ausserhalb 0x%08X..0x%08X"
                             % (a, dt.BASE, dt.BASE + dt.SIZE))

    case = dt.Case(name=f["name"] or ("sub_%08X" % va), code=code, regs=regs, mem=mem)
    case._ret_addr = dt.BASE + (ret_addr - va)
    asm = "; ".join(("%s %s" % (i.mnemonic, i.op_str)).strip() for i in insns)

    print("Funktion %s (0x%08X, %d B)  + ret abgeschnitten" % (f["name"], va, f["size"]))
    print("Code: %s" % asm)
    print("Startregs: %s" % ({**dt.DEFAULT_REGS, **regs}))

    want = dt.run_unicorn(case)

    workdir = tempfile.mkdtemp(prefix="difftest-fn-")
    try:
        got = dt.run_lifted([case], workdir, args.keep)[0]
    finally:
        if not args.keep:
            shutil.rmtree(workdir, ignore_errors=True)
        else:
            print("generierter C Quelltext in %s" % workdir)

    print("\n%-6s %10s %10s" % ("Feld", "lifted", "cpu"))
    for n in dt.REGS:
        mark = "" if got["regs"][n] == want["regs"][n] else "  <-- DIFF"
        print("%-6s %10X %10X%s" % (n, got["regs"][n], want["regs"][n], mark))
    efl_mark = "" if got["eflags"] == want["eflags"] else "  <-- DIFF"
    print("%-6s %10X %10X%s" % ("EFLAGS", got["eflags"], want["eflags"], efl_mark))

    fields = dt.diff(case, got, want)
    if fields:
        print("\nABWEICHUNGEN: %d" % len(fields))
        for name, a, b in fields:
            print("  %-10s lifted %8s   cpu %8s" % (name, a, b))
        return 1
    print("\nOK: lifted == CPU (alle Register, Flags, Speicher).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
