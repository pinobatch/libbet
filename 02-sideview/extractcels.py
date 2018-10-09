#!/usr/bin/env python
"""
Extract sprite cels from an image

# Leading and trailing whitespace are ignored
# A line beginning with zero or more whitespace followed by a # sign
# is a comment and ignored.
# The file begins with file-wide things like palette declarations



# Then for each frame:

frame <nameofframe> <cliprect>?
strip <palette> <cliprect>?
hotspot <loc>

"""
from PIL import Image
import sys
import argparse
from collections import OrderedDict

# Parsing the strips file

class InputFrame(object):
    def __init__(self, parent, cliprect=None):
        self.parent = parent  # for 'repeats'
        self.cliprect = cliprect
        self.strips = []
        self.hotspot = None

    def add_strip(self, palette, rect=None):
        rect = rect or cliprect
        if not rect:
            raise TypeError("strip rect is required if no cliprect")
        l, t, w, h = rect
        lpad = tpad = 0
        if self.cliprect:
            cl, ct, cw, ch = self.cliprect
            w = min(w, cl + cw - l)
            h = min(h, ct + ch - t)
            if cl > l:
                lpad = cl - l
                w -= lpad
                l = cl
            if ct > t:
                tpad = ct - t
                h -= tpad
                t = ct
            if h <= 0 or w <= 0:
                print("warning: skipping strip rect %s outside clipping rect %s"
                      % (rect, self.cliprect), file=sys.stderr)
                return
        self.strips.append((palette, l, t, w, h, lpad, tpad))

    def add_hotspot(self, xy):
        self.hotspot = xy

    def get_cliprect(self):
        """Return the specified clipping rectangle or make a guess."""
        if self.cliprect: return self.cliprect

        # Guess cliprect based on strips
        l = r = self.strips[0][1][0]
        t = b = self.strips[0][1][1]
        for row in strips:
            sl, st, sw, sh = row[1:5]
            l = min(l, sl)
            t = min(t, st)
            r = max(r, sl + sw)
            b = max(b, st + sh)
        self.cliprect = l, t, r - l, b - t
        return self.cliprect

    def get_hotspot(self):
        """Return the specified hotspot or make a guess."""
        if self.hotspot: return self.hotspot

        # Guess hotspot based on cliprect bottom center
        cl, ct, cw, ch = self.get_cliprect()
        self.hotspot = cl + cw // 2, ct + ch
        return self.hotspot

class InputParser(object):
    def __init__(self, lines=None):
        self.linecount = 0
        self.frames = OrderedDict()
        self.cur_frame = None
        self.palettes = {}
        if lines:
            self.extend(lines)

    def extend(self, lines):
        for line in lines:
            self.append(line)

    def append(self, line):
        self.linecount += 1
        line = line.strip()
        if not line or line.startswith("#"): return
        words = line.split()
        try:
            wordcmd = self.wordcmds[words[0]]
        except KeyError:
            raise ValueError("unknown command " + words[0])
        try:
            wordcmd(self, words[1:])
        except Exception as e:
            raise ValueError("%d: %s" % (self.linecount, e))

    def add_frame(self, words):
        name, cliprect = words[0], None
        if name in self.frames:
            raise ValueError("duplicate definition of frame "+name)
        if len(words) == 5 and all(x.isdigit() for x in words[1:5]):
            cliprect = tuple(int(x) for x in words[1:5])
        elif len(words) != 1:
            raise ValueError("unrecognized arguments to frame "
                             + " ".join(words))
        self.frames[name] = InputFrame(self.frames, cliprect=cliprect)
        self.cur_frame = name

    def add_strip(self, words):
        frame = self.frames[self.cur_frame]
        palette, cliprect = int(words[0]), None
        if len(words) == 5 and all(x.isdigit() for x in words[1:5]):
            rect = tuple(int(x) for x in words[1:5])
        elif len(words) != 1:
            raise ValueError("unrecognized arguments to strip "
                             + " ".join(words))
        frame.add_strip(palette, rect=rect)

    def add_hotspot(self, words):
        if len(words) != 2:
            raise ValueError("unrecognized arguments to hotspot "
                             + " ".join(words))
        xy = tuple(int(x) for x in words)
        self.frames[self.cur_frame].add_hotspot(xy)

    wordcmds = {
        "frame": add_frame,
        "strip": add_strip,
        "hotspot": add_hotspot,
    }

# Extracting the tiles for each cel


# CLI front end

def parse_argv(argv):
    p = argparse.ArgumentParser()
    p.add_argument("STRIPSFILE")
    p.add_argument("CELIMAGE")
    return p.parse_args(argv[1:])

def main(argv=None):
    args = parse_argv(argv or sys.argv)
    im = Image.open(args.CELIMAGE)
    with open(args.STRIPSFILE, "r") as infp:
        doc = InputParser(infp)
    print(list(doc.frames))

if __name__=='__main__':
    if "idlelib" in sys.modules:
        main("""
extractcels.py Libbet.ec.txt spritesheet-side.png
""".split())
    else:
        main()
