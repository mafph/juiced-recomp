"""
patch_sections.py - markiert eine PE-Sektion als Daten (kein CODE/EXEC).

Erzeugt eine Kopie der Eingabe-EXE, in der fuer die genannten Sektionen die
Flags IMAGE_SCN_CNT_CODE (0x20) und IMAGE_SCN_MEM_EXECUTE (0x20000000) geloescht
werden. Bytes, Groessen und Adressen bleiben unveraendert. Zweck: pcrecomp
(pe_analyze/disasm32) ueberspringt diese Sektionen als Code.

Aufruf:
    python scripts/patch_sections.py Juiced.exe build/Juiced.pcrecomp.exe .securom
"""
import struct
import sys
import os

CNT_CODE = 0x20
MEM_EXECUTE = 0x20000000


def patch(src, dst, demote):
    with open(src, "rb") as f:
        data = bytearray(f.read())

    if data[:2] != b"MZ":
        raise SystemExit("kein MZ/PE")
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if data[e_lfanew:e_lfanew + 4] != b"PE\0\0":
        raise SystemExit("keine PE-Signatur")

    coff = e_lfanew + 4
    nsec = struct.unpack_from("<H", data, coff + 2)[0]
    optsize = struct.unpack_from("<H", data, coff + 16)[0]
    sec = coff + 20 + optsize

    changed = []
    for i in range(nsec):
        off = sec + i * 40
        name = data[off:off + 8].rstrip(b"\0").decode("latin1")
        if name in demote:
            chars = struct.unpack_from("<I", data, off + 36)[0]
            new = chars & ~(CNT_CODE | MEM_EXECUTE)
            struct.pack_into("<I", data, off + 36, new)
            changed.append((name, chars, new))
            print(f"  {name}: 0x{chars:08X} -> 0x{new:08X}")

    if not changed:
        print("  Hinweis: keine Ziel-Sektion gefunden.")

    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(dst, "wb") as f:
        f.write(data)
    print(f"Geschrieben: {dst}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit("Aufruf: patch_sections.py <in.exe> <out.exe> <sec> [<sec> ...]")
    patch(sys.argv[1], sys.argv[2], set(sys.argv[3:]))
