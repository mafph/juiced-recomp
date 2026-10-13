"""
patch_cc1_laa.py - setzt das LARGE_ADDRESS_AWARE-Flag (0x0020) im PE-Header der
32-Bit-GCC-/Binutils-Programme.

Hintergrund: Der i686-w64-mingw32-Compiler ist selbst 32-Bit. Ohne LAA stehen cc1
nur ~2 GB Adressraum zu; die groessten gelifteten TUs (bis 37 MB) lassen sich damit
nicht kompilieren ("cc1.exe: out of memory"). Auf einem 64-Bit-Windows erlaubt LAA
bis zu ~4 GB. ld.exe ist bereits LAA.

Sicher: es wird eine .bak_laa-Sicherung angelegt; idempotent.

Aufruf:
    python scripts/patch_cc1_laa.py [MSYS2_MINGW32_ROOT]   (Default: C:/msys64/mingw32)
"""
import glob
import os
import shutil
import struct
import sys

DEFAULT_ROOT = r"C:\msys64\mingw32"


def patch(path):
    data = bytearray(open(path, "rb").read())
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    ch = struct.unpack_from("<H", data, pe + 0x16)[0]
    if ch & 0x20:
        print("bereits LAA:", path)
        return
    if not os.path.exists(path + ".bak_laa"):
        shutil.copy2(path, path + ".bak_laa")
    struct.pack_into("<H", data, pe + 0x16, ch | 0x20)
    open(path, "wb").write(data)
    print("LAA gesetzt: %s (0x%04X -> 0x%04X)" % (path, ch, ch | 0x20))


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOT
    targets = (
        glob.glob(os.path.join(root, r"lib\gcc\i686-w64-mingw32\*\cc1.exe"))
        + glob.glob(os.path.join(root, r"lib\gcc\i686-w64-mingw32\*\cc1plus.exe"))
        + glob.glob(os.path.join(root, r"i686-w64-mingw32\bin\ld.exe"))
        + glob.glob(os.path.join(root, r"bin\ld.exe"))
    )
    if not targets:
        raise SystemExit("keine Ziele gefunden unter " + root)
    for t in targets:
        patch(t)


if __name__ == "__main__":
    main()
