import struct
import sys

def main(path):
    with open(path, "rb") as f:
        data = f.read()

    if data[:2] != b"MZ":
        print("Not an MZ/PE file"); return
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if data[e_lfanew:e_lfanew+4] != b"PE\0\0":
        print("No PE signature"); return

    coff = e_lfanew + 4
    machine, nsec, _, _, _, optsize, chars = struct.unpack_from("<HHIIIHH", data, coff)
    opt = coff + 20
    magic = struct.unpack_from("<H", data, opt)[0]
    imagebase = struct.unpack_from("<I", data, opt + 28)[0] if magic == 0x10B else struct.unpack_from("<Q", data, opt + 24)[0]

    print(f"machine=0x{machine:04X} sections={nsec} optmagic=0x{magic:X} imagebase=0x{imagebase:X}")
    print(f"{'name':10} {'VA':>10} {'VSize':>10} {'RawPtr':>10} {'RawSize':>10}  {'flags':>8}  {'RVAend':>10}")
    sec = opt + optsize
    for i in range(nsec):
        off = sec + i * 40
        name = data[off:off+8].rstrip(b"\0").decode("latin1")
        vsize, va, rawsize, rawptr = struct.unpack_from("<IIII", data, off + 8)
        flags = struct.unpack_from("<I", data, off + 36)[0]
        rva_end = va + max(vsize, rawsize)
        print(f"{name:10} 0x{va+imagebase:08X} 0x{vsize:08X} 0x{rawptr:08X} 0x{rawsize:08X}  0x{flags:08X}  0x{rva_end+imagebase:08X}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Juiced.exe")
