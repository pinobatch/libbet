#!/usr/bin/env python
from PIL import Image
import sys
import argparse


def parse_argv(argv):
    p = argparse.ArgumentParser()
    p.add_argument("STRIPSFILE")
    p.add_argument("CELIMAGE")
    return p.parse_args(argv[1:])

def main(argv=None):
    args = parse_argv(argv or sys.argv)
    im = Image.open(args.CELIMAGE)
    with open(args.STRIPSFILE, "r") as infp:
        lines = list(infp)
    for line in lines:
        print(line)
    im.show()

if __name__=='__main__':
    if "idlelib" in sys.modules:
        main("""
extractcels.py Libbet.ec.txt spritesheet-side.png
""".split())
    else:
        main()
