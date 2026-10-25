#!/usr/bin/env python3
"""IAT-Slot(s) aufloesen: VA -> DLL!Funktion (Import-Tabelle).

Juiced.exe ist *bound-imported*: die IAT-Slots enthalten auf Platte bereits
absolute DLL-Adressen (altes XP-Layout), keine RVAs/Namen. Dieses Skript
ordnet einem IAT-Slot bzw. einer gebundenen Adresse den Importnamen zu.

Beispiele:
    python scripts/iat_names.py 0x6CC1EC 0x6CC168        # IAT-Slot-VAs
    python scripts/iat_names.py --bound 0x7C812B6E       # gebundene Adresse
    python scripts/iat_names.py --all                    # alle Importe
"""
import argparse
import struct
import sys

import pefile


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("vas", nargs="*", help="IAT-Slot-VA oder (mit --bound) gebundene Adresse")
    ap.add_argument("--pe", default="Juiced.exe", help="PE-Datei (Default: Juiced.exe)")
    ap.add_argument("--bound", action="store_true",
                    help="Argumente sind gebundene Adressen (IAT-Inhalt), nicht Slot-VAs")
    ap.add_argument("--all", action="store_true", help="alle Importe auflisten")
    args = ap.parse_args()

    pe = pefile.PE(args.pe, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
    raw = open(args.pe, "rb").read()

    by_slot = {}
    by_bound = {}
    for d in pe.DIRECTORY_ENTRY_IMPORT:
        dll = d.dll.decode(errors="replace")
        for imp in d.imports:
            name = imp.name.decode(errors="replace") if imp.name else "ord %d" % imp.ordinal
            by_slot[imp.address] = (dll, name)
            try:
                off = pe.get_offset_from_rva(imp.address - pe.OPTIONAL_HEADER.ImageBase)
                bound = struct.unpack("<I", raw[off:off + 4])[0]
                by_bound.setdefault(bound, []).append((imp.address, dll, name))
            except Exception:
                pass

    if args.all:
        for slot in sorted(by_slot):
            dll, name = by_slot[slot]
            print("0x%08X  %s!%s" % (slot, dll, name))
        return 0

    rc = 0
    for v in args.vas:
        va = int(v, 0)
        if args.bound:
            hits = by_bound.get(va, [])
            if not hits:
                print("0x%08X  <kein Import mit diesem gebundenen Wert>" % va)
                rc = 1
            for slot, dll, name in hits:
                print("0x%08X  slot 0x%08X  %s!%s" % (va, slot, dll, name))
        else:
            hit = by_slot.get(va)
            if not hit:
                print("0x%08X  <kein IAT-Slot>" % va)
                rc = 1
            else:
                dll, name = hit
                try:
                    off = pe.get_offset_from_rva(va - pe.OPTIONAL_HEADER.ImageBase)
                    bound = struct.unpack("<I", raw[off:off + 4])[0]
                    print("0x%08X  %s!%s  (gebunden: 0x%08X)" % (va, dll, name, bound))
                except Exception:
                    print("0x%08X  %s!%s" % (va, dll, name))
    return rc


if __name__ == "__main__":
    sys.exit(main())
