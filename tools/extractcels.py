#!/usr/bin/env python3
"""
Extract sprite cels from an image

Copyright 2018-2023 Damian Yerrick

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must not
   claim that you wrote the original software. If you use this software
   in a product, an acknowledgment in the product documentation would be
   appreciated but is not required.
2. Altered source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.
3. This notice may not be removed or altered from any source distribution.
"""
"""Cel position file

The cel position (.ec) file is a source code file that describes
where the cels are located on a .png sprite sheet and where the
non-transparent rectangles of sprite tiles lie within each cel.

Leading and trailing whitespace on each line are ignored.
A line beginning with zero or more whitespace followed by a `#` sign
is a comment and ignored.
The file begins with file-wide things like palette declarations:

    backdrop <#rgb>
    palette <palid> <#rgb> <#rgb> <#rgb> <#rgb>=2 <#rgb>=3

Keywords and types used in global declarations:

- `backdrop` tells what color is used for pixels that are always
  transparent.
- `palette` associates a palette ID with one or more colors in the
  image.  On Game Boy, bit 4 specifies a DMG palette (`0` for OBP0 or
  `16` for OBP1), and bits 2-0 specify a GBC palette ID (`0` to `7`).
  The first three `#rgb` values are associated with indices 1-3
  unless overridden with a following `=1`, `=2`, or `=3` to force a
  color to be converted to a particular index.
- An <#rgb> specifies an RGB color using 3- or 6-digit hexadecimal,
  such as `#fa9` or `#ffaa99`.

Then for each cel:

    frame <nameofframe> <cliprect>?
      strip <palette> <cliprect>?
      strip <palette> <cliprect> at <loc>
      hotspot <loc>

Keywords and types used in cels:

- Each `frame` begins and names one cel and optionally specifies a
  clipping rectangle.  (If a clipping rectangle is not provided,
  it uses the union of all strips' clipping rectangles.)
- Each `strip` marks a rectangle of non-transparent pixels within
  that cel using one palette.  A cel may have multiple strips to
  minimize wasted space or maximize tile reuse.  If the strip does
  not specify a clipping rectangle, it uses that of the `frame`.
  A strip may specify a destination location to place the pixels read
  from its clipping rectangle at a different position when drawn.
  This is useful for advanced tile reuse scenarios.
- `hotspot` gives the starting position used to calculate the offset
  of each rectangle when the cel is drawn.  It defaults to the
  bottom center of the `frame`'s clipping rectangle.
- A clipping rectangle `<cliprect>` is four integers of the form
  `<left> <top> <width> <height>`, specifying a region of the image.
- A `<palette>` tells what palette ID to use for this strip, as a
  cel may have multiple adjacent or overlaid strips with different
  palettes.  This must match an ID in a `palette` declaration.
- A location `<loc>` is two integers of the form `<left> <top>`,
  specifying either a hotspot or the top left of a strip's
  destination.
"""
from PIL import Image, ImageDraw
import os, sys, argparse, re
from collections import OrderedDict
import pilbmp2nes

# Parsing the strips file

def parseint(s):
    if s.startswith("$"): return int(s[1:], 16)
    if s.startswith("0x"): return int(s[2:], 16)
    return int(s)

def isint(s):
    try:
        parseint(s)
    except ValueError:
        return False
    return True

class InputFrame(object):
    def __init__(self, parent, cliprect=None):
        self.parent = parent  # for 'repeats'
        self.cliprect = cliprect
        self.strips = []
        self.hotspot = None

    def add_strip(self, palette, rect=None, dstpos=None):
        rect = rect or cliprect
        if not rect:
            raise TypeError("strip rect is required if no cliprect")
        if not 0 <= palette < 32:
            raise TypeError("palette must be 0 to 31; got %d" % palette)
        l, t, w, h = rect
        dstl, dstt = dstpos or (l, t)
        lpad = tpad = 0
        if self.cliprect and not dstpos:
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
        self.strips.append((palette, l, t, w, h, lpad, tpad, dstl, dstt))

    def add_hotspot(self, xy):
        self.hotspot = xy

    def get_cliprect(self):
        """Return the specified clipping rectangle or make a guess."""
        if self.cliprect: return self.cliprect

        # Guess cliprect based on destination bounding boxes of strips
        l, t = r, b = self.strips[0][7:9]
        for row in self.strips:
            sw, sh = row[3:5]
            sl, st = row[7:9]
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

colorRE = re.compile('#([0-9a-fA-F]{3,6})$')
def parse_color(s):
    """Parse a 3 or 6 digit hex color (#FFF or #FFFFFF) into a 3-tuple or None"""
    m = colorRE.match(s)
    if m:
        m = m.group(1)
        if len(m) == 3:
            return tuple(int(c, 16) * 17 for c in m)
        elif len(m) == 6:
            return tuple(int(m[i:i + 2], 16) for i in range(0, 6, 2))
    raise ValueError("color %s not recognized" % s)

def parse_subpalette(words):
    """Turn palette entry into a list of color-to-index mappings.

For example, #AAA=2 or #AAAAAA=2 means that (170, 170, 170) will be
recognized as color 2 in that subpalette.
If no =number is specified, indices are recognized sequentially from 1.

Return a list of ((r, g, b), index) tuples.
"""
    out = []
    for i, word in enumerate(words):
        color_index = word.split("=", 1)
        color = parse_color(color_index[0])
        index = int(color_index[1]) if len(color_index) > 1 else i + 1
        out.append((color, index))
    return out

class InputParser(object):
    def __init__(self, lines=None):
        self.linecount = 0
        self.frames = OrderedDict()
        self.cur_frame = None
        self.palettes = {}
        self.backdrop = (255, 0, 255)
        self.global_palette = self.global_to_local = None
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
        isdig = [isint(x) for x in words]
        name, cliprect = words[0], None
        if name in self.frames:
            raise ValueError("duplicate definition of frame "+name)
        self.frames[name] = InputFrame(self.frames)
        self.cur_frame = name
        if len(words) == 5 and all(isdig[1:5]):
            self.frames[name].cliprect = tuple(int(x) for x in words[1:5])
        elif len(words) == 3 and words[1] == 'repeats':
            self.add_repeats(words[2:])
        elif len(words) != 1:
            raise ValueError("unrecognized arguments to frame "
                             + " ".join(words))

    def add_repeats(self, words):
        if len(words) != 1:
            raise ValueError("unrecognized arguments to repeats "
                             + " ".join(words))
        frame = self.frames[self.cur_frame]
        srcframe = self.frames[words[0]]
        frame.strips[:] = srcframe.strips
        frame.cliprect = srcframe.cliprect

    def add_strip(self, words):
        isdig = [isint(x) for x in words]
        frame = self.frames[self.cur_frame]
        palette, rect, dstpos = parseint(words[0]), frame.cliprect, None
        if len(words) in (5, 8) and all(isdig[1:5]):
            rect = tuple(parseint(x) for x in words[1:5])
            if len(words) == 8:
                if words[5] == 'at' and all(isdig[6:8]):
                    dstpos = tuple(parseint(x) for x in words[6:8])
                else:
                    raise ValueError("unrecognized destination in strip "
                                     + " ".join(words))
        elif len(words) != 1:
            raise ValueError("unrecognized arguments to strip "
                             + " ".join(words))
        frame.add_strip(palette, rect=rect, dstpos=dstpos)

    def add_hotspot(self, words):
        if len(words) != 2:
            raise ValueError("unrecognized arguments to hotspot "
                             + " ".join(words))
        xy = tuple(parseint(x) for x in words)
        self.frames[self.cur_frame].add_hotspot(xy)

    def add_backdrop(self, words):
        if len(words) != 1:
            raise ValueError("only 1 word allowed")
        self.backdrop = parse_color(words[0])

    def add_palette(self, words):
        paletteid = parseint(words[0])
        colors = parse_subpalette(words[1:])
        self.palettes[paletteid] = colors

    def calc_global_palette(self):
        """Calculate a 256-entry palette containing all subpalettes.

Convert self.palette to these:

- self.global_palette, a 768-byte bytes containing the backdrop and
  all subpalettes defined in the cel list
- self.global_to_local, a dict from self.palettes keys to 256-byte
  bytes representing mappings from indices in self.global_palette
  to indices in the subpalette, intended as LUTs for im.point()
"""
        seencolors = {self.backdrop: 0}
        self.global_to_local = {}
        for paletteid, colors in self.palettes.items():
            self.global_to_local[paletteid] = g2l = bytearray(256)
            for color, index in colors:
                seencolors.setdefault(color, len(seencolors))
                g2l[seencolors[color]] = index

        palette = [bytes(self.backdrop)] * 256
        for color, index in seencolors.items():
            palette[index] = bytes(color)
        self.global_palette = b"".join(palette)

    wordcmds = {
        "frame": add_frame,
        "repeats": add_repeats,
        "strip": add_strip,
        "hotspot": add_hotspot,
        "palette": add_palette,
        "backdrop": add_backdrop,
    }

# Extracting the tiles for each cel

def quantizetopalette(src, palette, dither=False):
    """Convert an RGB or L mode image to use a given P image's palette.

Requires Pillow 6 or later.
Reference: https://stackoverflow.com/a/29438149/2738262
"""
    return src.quantize(palette=palette, dither=1 if dither else 0)

def apply_global_palette(im, doc):
    if not doc.global_palette:
        doc.calc_global_palette()
    palim = Image.new("P", (16, 16))
    palim.putpalette(doc.global_palette)
    return quantizetopalette(im.convert("RGB"), palim)

TILE_W = 8
TILE_PLANEMAP = "0,1"
BPP = 2

def read_strip(im, strip, g2l, hotspot, tile_ht, verbose=False):
    paletteid, l, t, w, h, lpad, tpad, dstl, dstt = strip

    # Crop and convert to subpalette
    cropped = im.crop((l, t, l + w, t + h)).point(g2l[paletteid])

    # Add padding at left and top for exceeding the crop rect,
    # and at right and bottom to a multiple of one tile
    wnew = -(-(w + lpad) // TILE_W) * TILE_W
    hnew = -(-(h + tpad) // tile_ht) * tile_ht
    padded = Image.new('P', (wnew, hnew), 0)
    padded.paste(cropped, (lpad, tpad))

    # Convert image to tiles
    tilefmt = lambda x: pilbmp2nes.formatTilePlanar(x, TILE_PLANEMAP)
    striptiles = pilbmp2nes.pilbmp2chr(padded, TILE_W, tile_ht, tilefmt)

    # Join top and bottom halves of 8x16-pixel tiles
    tiles_per_obj = -(-tile_ht // 8)
    striptiles = [
        b''.join(striptiles[i:i + tiles_per_obj])
        for i in range(0, len(striptiles), tiles_per_obj)
    ]

    # Convert coords to hotspot-relative
    dstl -= hotspot[0]
    dstt -= hotspot[1]

    # Convert tiles to horizontal strips
    objs_per_row = wnew // TILE_W
    tend = 0
    for y in range(hnew // tile_ht):
        tstart, tend = tend, tend + objs_per_row
        row_x, row_tiles = dstl, striptiles[tstart:tend]
        row_y = dstt + y * tile_ht

        r_removed = l_removed = 0
        while row_tiles and not any(row_tiles[-1]):
            del row_tiles[-1]
            r_removed += 1
        while row_tiles and not any(row_tiles[0]):
            del row_tiles[0]
            row_x += TILE_W
            l_removed += 1
        if verbose and (l_removed or r_removed):
            prefix = "strip %d %d %d %d %d" % (paletteid, l, t, w, h)
            if row_tiles:
                print("%s: trimming blank objects at y=%d (%d left, %d right)"
                      % (prefix, y * tile_ht + t + tpad, l_removed, r_removed),
                      file=sys.stderr)
            else:
                print("%s: skipping blank row" % (prefix,), file=sys.stderr)
        if row_tiles:
            yield paletteid, row_tiles, row_x, row_y

def read_all_strips(im, doc, tile_ht, verbose=False):
    out = []
    for framename, frame in doc.frames.items():
        hotspot = frame.get_hotspot()
        strips = []
        gtl = doc.global_to_local
        for strip in frame.strips:
            strips.extend(read_strip(im, strip, gtl, hotspot, tile_ht,
                                     verbose=verbose))
        out.append(strips)
    return out

# Finding duplicate tiles

def get_bitreverse():
    """Get a lookup table for horizontal flipping."""
    br = bytearray([0x00, 0x80, 0x40, 0xC0])
    for v in range(6):
        bit = 0x20 >> v
        br.extend(x | bit for x in br)
    return br

bitreverse = get_bitreverse()

def hflipGB(tile):
    br = bitreverse
    return bytes(br[b] for b in tile)

def vflipGB(tile):
    return b"".join(tile[i:i + 2] for i in range(len(tile) - 2, -2, -2))

def flipuniq(it):
    """Convert an iterable of Game Boy tiles (8x8 or 8x16) to unique tiles.

Return a 2-tuple (tiles, tilemap), where tiles is only the unique
tiles, and tilemap is a list of references to tiles:
bits 12-0: tile number
bit 13: horizontal flip (bit-reverse)
bit 14: vertical flip (reverse order of 16-bit entities)
"""
    tiles = []
    tile2id = {}
    tilemap = []
    for tile in it:
        if tile not in tile2id:
            tilenum = len(tiles)
            hf = hflipGB(tile)
            vf = vflipGB(tile)
            vhf = vflipGB(hf)
            tile2id[vhf] = tilenum | 0x6000
            tile2id[vf] = tilenum | 0x4000
            tile2id[hf] = tilenum | 0x2000
            tile2id[tile] = tilenum
            tiles.append(tile)
        tilemap.append(tile2id[tile])
    return tiles, tilemap

# Visualize the conversion

def stripsvis(backim, frames):
    # ImageDraw ellipse is very ugly.  Use rects to draw something
    # slightly less ugly.
    ellipseborderrects = [
        (-3, -2, -3, 1),
        (2, -2, 2, 1),
        (-2, -3, 1, -3),
        (-2, 2, 1, 2)
    ]
    
    backim = backim.convert("RGB").resize((backim.size[0]*2, backim.size[1]*2),
                                          Image.NEAREST)
    dc = ImageDraw.Draw(backim)
    try:
        frames = frames.values()
    except AttributeError:
        pass
    for frame in frames:
        cl, ct, cw, ch = frame.get_cliprect()
        dc.rectangle((cl * 2, ct * 2, (cl + cw) * 2 - 1, (ct + ch) * 2 - 1),
                     outline=(0, 0, 255))
        for row in frame.strips:
            sl, st, sw, sh = row[1:5]
            dc.rectangle((sl * 2, st * 2, (sl + sw) * 2 - 1, (st + sh) * 2 - 1),
                         outline=(0, 255, 255))
        hx, hy = frame.get_hotspot()
        for el, et, er, eb in ellipseborderrects:
            dc.rectangle((hx * 2 + el, hy * 2 + et, hx * 2 + er, hy * 2 + eb),
                         fill=(255, 0, 0))
    return backim

def sliver_to_texels(lo, hi):
    return bytes(((lo >> i) & 1) | (((hi >> i) & 1) << 1)
                 for i in range(7, -1, -1))

def tile_to_texels(chrdata):
    _stt = sliver_to_texels
    return b''.join(_stt(a, b) for (a, b) in zip(chrdata[0::2], chrdata[1::2]))

##PREVIEWPALETTE = bytes.fromhex('CCCC4488AA44448844006644')
PREVIEWPALETTE = bytes.fromhex('AAAAFF000000AAAAAAFFFFFF')

def gbtilestoim(tiles, num_cols=16):
    tile_height_px = len(tiles[0]) // BPP
    num_rows = -(-len(tiles) // num_cols)
    im = Image.new('P', (num_cols * TILE_W, num_rows * tile_height_px), 0)
    onetile = Image.new('P', (TILE_W, tile_height_px), 0)
    x = y = 0
    for tile in tiles:
        ttt = tile_to_texels(tile)
        onetile.putdata(ttt)
        im.paste(onetile, (x, y))
        x += TILE_W
        if x >= im.size[0]:
            x, y = 0, y + tile_height_px

    previewpalette = bytes(PREVIEWPALETTE)
    previewpalette += previewpalette[:3] * 252
    im.putpalette(previewpalette)
    return im

def pack_frames(framestrips, nt,
                streaming=False, verbose=False, tileid_factor=1):
    """Pack the frames in

streaming -- if true, find all the unique tiles first

Return a list of lists of bytes, one for each frame.
"""
    ntoffset = 0
    out = []
    for strips in framestrips:
        strip = []  # the byte strings that make up one frame
        pnxy = []
        frame_tilenums = set()
        for palette, tiles, x, y in strips:
            ntiles = len(tiles)
            ntend = ntoffset + ntiles
            assert -128 <= x < 128 and -128 <= y < 128
            assert 0 < ntiles <= 8
            assert 0x00 <= palette < 0x20
            tilenums = nt[ntoffset:ntend]
            frame_tilenums.update(x & 0xFF for x in tilenums)
            ntoffset = ntend
            pnxy.append((palette, tilenums, x, y))

        if streaming:
            # List all tiles that make up this frame
            # so the drawing code can copy them to VRAM
            frame_tilenums = sorted(frame_tilenums)
            iframe_tilenums = {v: k for k, v in enumerate(frame_tilenums)}
            b = [len(frame_tilenums)]
            b.extend(frame_tilenums)
            if verbose:
                print("Frame uses tiles %s"
                      % " ".join("%02x" % x for x in frame_tilenums),
                      file=sys.stderr)
            strip.append(bytes(b))

        for palette, tilenums, x, y in pnxy:
            if streaming:
                if verbose:
                    print("mapping tilenums "
                          + " ".join("%04x" % x for x in tilenums),
                          file=sys.stderr)
                tilenums = [
                    (x & 0x6000) | iframe_tilenums[x & 0xFF]
                    for x in tilenums
                ]
                if verbose:
                    print("  to frame-local "
                          + " ".join("%04x" % x for x in tilenums),
                          file=sys.stderr)
            b = bytearray([y + 128, x + 128,
                           palette | ((len(tilenums) - 1) << 5)])
            b.extend(((x & 0x6000) >> 7) | ((x * tileid_factor) & 0x3F)
                     for x in tilenums)
            strip.append(bytes(b))
        strip.append(b"\x00")
        out.append(strip)
    return out

def emit_frames(framestrips, nt, framenames,
                streaming=False, verbose=False, tileid_factor=1):
    out = [" dw mspr_" + n for n in framenames]
    ntoffset = 0
    packed = pack_frames(framestrips, nt, streaming=streaming,
                         verbose=verbose, tileid_factor=tileid_factor)

    # Consider only unique framedefs
    allframedefs = OrderedDict()
    for framename, framedef in zip(framenames, packed):
        joineddef = b"".join(framedef)
        if joineddef not in allframedefs:
            allframedefs[joineddef] = ([], framedef)
        allframedefs[joineddef][0].append(framename)

    for thisframenames, framedef in allframedefs.values():
        out.extend("mspr_%s:" % framename for framename in thisframenames)
        out.extend(
            " db " + ",".join("$%02x" % b for b in strip)
            for strip in framedef
        )

    out.extend("def FRAME_%s equ %d" % (n, i) for i, n in enumerate(framenames))
    out.extend(" export FRAME_%s" % (n,) for n in framenames)
    if streaming:
        max_count = max(framedef[0][0] for framedef in packed) if packed else 0
        out.append("; Maximum tiles per frame: %d" % max_count)
    return "\n".join(out)

# CLI front end

def parse_argv(argv):
    p = argparse.ArgumentParser()
    p.add_argument("STRIPSFILE")
    p.add_argument("CELIMAGE")
    p.add_argument("CHRFILE", nargs="?",
                   help="where to write unique tiles")
    p.add_argument("ASMFILE", nargs="?",
                   help="where to write asm")
    p.add_argument("--streaming", action="store_true",
                   help="prefix each cel with tile numbers (limit 256 instead of 64)")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="print debug info and write preview images")
    p.add_argument("--8x16", action="store_true", dest="is_8x16",
                   help="use 8x16 pixel sprites (experimental)")
    return p.parse_args(argv[1:])

def main(argv=None):
    args = parse_argv(argv or sys.argv)
    tile_ht = 16 if args.is_8x16 else 8
    im = Image.open(args.CELIMAGE)
    with open(args.STRIPSFILE, "r") as infp:
        doc = InputParser(infp)
    im = apply_global_palette(im, doc)

    framestrips = read_all_strips(im, doc, tile_ht, verbose=args.verbose)
    alltiles = [
        tile for frame in framestrips for row in frame for tile in row[1]
    ]
    utiles, nt = flipuniq(alltiles)

    if args.verbose:
        print("%d frames, %d tiles, %d unique"
              % (len(doc.frames), len(nt), len(utiles)),
              file=sys.stderr)
        stripsvis(im, doc.frames).save("_stripsvis.png")
        gbtilestoim(alltiles).save("_alltiles.png")
        gbtilestoim(utiles).save("_utiles.png")
    if args.CHRFILE:
        with open(args.CHRFILE, "wb") as outfp:
            outfp.writelines(utiles)
    if args.ASMFILE:
        ef = emit_frames(framestrips, nt, list(doc.frames),
                         streaming=args.streaming, verbose=args.verbose,
                         tileid_factor=2 if args.is_8x16 else 1)
        if args.ASMFILE == '-':
            sys.stdout.write(ef)
        else:
            with open(args.ASMFILE, "w") as outfp:
                outfp.write(ef)

if __name__=='__main__':
    if "idlelib" in sys.modules and len(sys.argv) < 2:
        import shlex
        main(shlex.split("""
extractcels.py -v --streaming ../tilesets/Mindy.ec ../tilesets/Mindy.png "" -
"""))
    else:
        main()
