#!/usr/bin/env python3
"""
beforefix.py
Tool to diagnose an RGBLINK logic error

Copyright 2024 Damian Yerrick
(insert zlib license here)
"""
"""
Before running RGBFIX, consider running this to make sure the
linker isn't writing some other section on top of the section
containing the header.
<https://github.com/gbdev/rgbds/issues/1350>
"""
import os, sys, argparse


def parse_argv(argv):
    p = argparse.ArgumentParser(
        description="Checks whether a ROM is ready for RGBFIX.",
        epilog="A ROM is ready if 0x100-0x14F are "
        "0x00 0xC3 PCL PCH, then 76 00's, with PCH < $40 (or < $80 if 32K). "
        "Exit with code 0 if ready or 1 and a diagnostic if not."
    )
    p.add_argument("romfile")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="always write hex dump and other details")
    return p.parse_args(argv[1:])

def canonical_hexdump(data, offset_add=0):
    """Output a bytes-like in the format of the hd utility."""
    for i in range(0, len(data), 16):
        row = data[i:i + 16]
        sanitized = bytes(x if 0x20 <= x < 0x7F else 0x2E for x in row)
        halves = [row[:8], row[8:]]
        halves = ["".join("%02x " % x for x in row) for row in halves]
        yield ("%08x  %-25s%-25s|%s|\n"
               % (i + offset_add, *halves, sanitized.decode("ascii")))

def main(argv=None):
    args = parse_argv(argv or sys.argv)
    is_32k_rom = False
    write_hexdump = args.verbose
    with open(args.romfile, "rb") as infp:
        infp.read(0x100)
        header = infp.read(0x50)
        is_32k_rom = len(infp.read(0x8000)) <= 0x8000 - 0x150
    okay = (header[0] == 0x00 and header[1] == 0xC3 and header[3] < 0x80
            and not any(header[4:]) and len(header) == 0x50)
    if header[3] >= 0x40 and not is_32k_rom: okay = False
    if not okay: write_hexdump = True
    if write_hexdump:
        print("beforefix.py: %s: %s"
              % (args.romfile, "unbanked" if is_32k_rom else "banked"),
              file=sys.stderr)
        sys.stderr.writelines(canonical_hexdump(header, 0x100))
    if not okay:
        print("beforefix.py: %s: header not ready for RGBFIX"
              % (args.romfile,), file=sys.stderr)
        exit(1)

if __name__=='__main__':
    if 'idlelib' in sys.modules:
        main("""
./beforefix.py -v ../libbet.gb
""".split())
    else:
        main()
