#!/usr/bin/env python3
"""
the file format:

# establish a camera and backdrop
size 160 144
bgcolor #CCC

# load a sprite sheet
sheet Nander nander.png

# set the last sprite sheet's transparent color key, as a web color
# if RGB or a color index if indexed.  Changing it after the first
# use in an output frame is undefined.
sheetbg 0

# divide it into cels by name, left, top, width, height,
# and optional hotspot (if not center of box)
cel Ne1   0 16  8  8
cel Ne2  16 16 16  8  22 20
cel Ne3  32 16 16  8
cel Ne4  48 16 16  8  58 20

# A cel sequence associated with a sprite sheet adds automatic
# movement and cel changing to a layer.
celseq walk_e
move Ne1 by 2 0
move Ne2 by 2 0
move Ne3 by 2 0
move Ne4 by 2 0

# Cels for a cel sequence can no longer be accepted after a
# layer or wait command.

# load a sprite sheet onto a layer
layer 1 Nander Ne1 4 12

# finish this frame and wait n milliseconds (10 should divide n)
wait 200

# move this layer and change its frame
# 'by' adds to position; 'to' replaces the position; 'flip' changes
# the reflection to x, y, xy, or None; any other changes the cel
move 1 Ne2 by 2 0
wait 200

# hide a layer
hide 1

# A bug in either Pillow or GIMP occasionally makes some
# frames corrupt in such a way that GIMP stops loading
# them and produces the following error message:
#     GIF: too much input data, ignoring extra...
# To work around this, break the GIF into segments.
# Load the first using File > Open (Ctrl+O), and add
# the rest using File > Open as Layers (Ctrl+Alt+O).
# Sometimes even this isn't enough, and you need to output in
# .ora format (zipped PNGs with XML layering) instead of .gif.
segment


"""
import os
import sys
import re
import argparse
from PIL import Image, ImageChops
from contextlib import closing
from collections import namedtuple
from types import SimpleNamespace

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

def make_ora_from_frames(frames):
    """Create OpenRaster data from a list of (image, duration) tuples

OpenRaster is defined at
https://www.freedesktop.org/wiki/Specifications/OpenRaster/Draft/

Return a byte string ready to be written to a file whose name ends in
.ora or sent over the Internet with Content-type: image/openraster
"""
    import zipfile
    from io import BytesIO
    from html import escape as H
    zipfp = BytesIO()
    lastframe = None
    with closing(zipfile.ZipFile(zipfp, "w", zipfile.ZIP_STORED)) as ora:
        layers = []
        im0size = None
        for i, (im, duration) in enumerate(frames):
            # Perform the same dirty rectangle optimization that
            # Pillow's (semi-broken) animated GIF export performs.
            # Can be improved by replacing horizontal rows where
            # difference is black but im has more than one color
            # with transparency, as GIMP's GIF optimizer does.
            if lastframe is not None:
                imdiff = ImageChops.difference(lastframe.convert("RGB"), im.convert("RGB"))
                diffbox = imdiff.getbbox()
                if diffbox is None:
                    im.show()
                layer_x, layer_y = diffbox[:2]
                imcrop = im.crop(diffbox)
            else:
                imcrop, im0size, layer_x, layer_y = im, im.size, 0, 0

            layername = (
                "Frame %d (%dms)%s"
                % (i + 1, duration, "(combine)" if lastframe else "")
            )
            layerfilename = "data/f%04d.png" % (i + 1)
            layers.append((layername, layerfilename, layer_x, layer_y))
            with BytesIO() as imfp:
                imcrop.save(imfp, format="PNG")
                ora.writestr(layerfilename, imfp.getvalue())
            lastframe = im

        # OpenRaster requires preview at 2 sizes
        if lastframe.mode not in ('RGB', 'RGBA'):
            lastframe = lastframe.convert("RGBA")
        with BytesIO() as imfp:
            lastframe.save(imfp, format="PNG")
            ora.writestr("mergedimage.png", imfp.getvalue())
        lastframe.thumbnail((256, 256))
        with BytesIO() as imfp:
            lastframe.save(imfp, format="PNG")
            ora.writestr("Thumbnails/thumbnail.png", imfp.getvalue())

        # Form layer stack
        stackxml = ["""<?xml version='1.0' encoding='UTF-8'?>
<image version="0.0.3" w="%d" h="%d" xres="96" yres="96"><stack>"""
                 % im0size]
        stackxml.extend(
            '<layer name="%s" src="%s" x="%d" y="%d" />'
            % (H(layername), H(layerfilename), x, y)
            for layername, layerfilename, x, y in reversed(layers)
        )
        stackxml.append("</stack></image>")
        stackxml = "\n".join(stackxml).encode("utf-8")
        ora.writestr("mimetype", b"image/openraster")
        ora.writestr("stack.xml", stackxml)

    return zipfp.getvalue()

flipnames = {
    'none': (None, 0),
    'x': (Image.FLIP_LEFT_RIGHT, 1),
    'h': (Image.FLIP_LEFT_RIGHT, 1),
    'y': (Image.FLIP_TOP_BOTTOM, 2),
    'v': (Image.FLIP_TOP_BOTTOM, 2),
    'xy': (Image.ROTATE_180, 3),
    'yx': (Image.ROTATE_180, 3),
    'hv': (Image.ROTATE_180, 3),
    'vh': (Image.ROTATE_180, 3),
}

Sheet = namedtuple('Sheet', 'im, filename, cels, celseqs')
Cel = namedtuple('Cel', 'x, y, w, h, cx, cy')
Layer = namedtuple('Layer', 'sheetname, cel, x, y, flip, seqstep')
CelSeqStep = namedtuple('CelSeqStep', 'cel, x, y')

class Job(object):
    def __init__(self, lines=None):
        self.frames = []
        self.sheets = {}
        self.layers = {}
        self.linecount = 1
        self.segment_breaks = {0}
        self.curframe = self.cursheet = self.curcelseq = None
        self.imsize = self.imsize_linenum = self.bgcolor = None
        self.skipping = False
        if lines: self.extend(lines)

    def append(self, line):
        self.linecount += 1
        line = line.strip()
        if line == '' or line.startswith('#'): return
        line = line.split()
        handler = self.wordhandlers[line[0]]
        handler(self, line)

    def extend(self, lines):
        for line in lines:
            self.append(line)

    def save(self, filename):
        segment_breaks = sorted(self.segment_breaks)
        segment_breaks.append(len(self.frames))
        namepart, extpart = os.path.splitext(filename)
        for s, e in zip(segment_breaks, segment_breaks[1:]):
            if len(segment_breaks) > 2:
                outfilename = "%s_%d%s" % (namepart, s, extpart)
                print("%s: writing %s" % (txtname, outfilename))
            else:
                outfilename = filename
            extlower = extpart.lower()

            if extlower == '.gif':
                first_cel = self.frames[s][0]
                subsequent_cels = [f[0] for f in self.frames[s + 1:e]]
                cel_durations = [f[1] for f in self.frames[s:e]]
                first_cel.save(
                    outfilename,
                    save_all=True,  # make animation
                    append_images=subsequent_cels,  # frames after first
                    duration=cel_durations,  # in milliseconds
                    loop=0
                )
            elif extlower == '.ora':
                filedata = make_ora_from_frames(self.frames[s:e])
                with open(outfilename, "wb") as outfp:
                    outfp.write(filedata)
            else:
                raise ValueError("unknown extension %s" % extpart)

    def handle_size(self, line):
        if self.imsize_linenum is not None:
            raise ValueError("size already set on line %d"
                             % (self.imsize_linenum))
        self.imsize = tuple(int(x) for x in line[1:3])
        self.imsize_linenum = self.linecount

    def handle_bgcolor(self, line):
        if len(line) >= 2:
            self.bgcolor = parse_color(line[1])
        else:
            self.bgcolor = None

    def handle_sheet(self, line):
        self.cursheet, imname = line[1], " ".join(line[2:])
        im = Image.open(imname)
        self.sheets[self.cursheet] = Sheet(im, imname, {}, {})

    def handle_sheetbg(self, line):
        """Change a sheet's transparent background color"""
        im = self.sheets[self.cursheet].im
        nbands = len(im.getbands())
        if len(line) == 2 and line[1].startswith('#'):
            color = parse_color(line1)
        else:
            color = tuple(int(x) for x in line[1:])
        if nbands != len(line) - 1:
            raise ValueError("expected %d bands; got %d"
                             % (nbands, len(color)))
        if len(color) == 1: color = color[0]
        im.info["transparency"] = color

    def handle_cel(self, line):
        """Add a cel's boundaries to a sprite sheet"""
        thissheet = self.sheets[self.cursheet]
        celname = line[1]
        if len(line) >= 6:
            l, t, w, h = (int(x) for x in line[2:6])
        else:
            w, h = thissheet.im.size  # cel is full size of sheet
            l = t = 0
        if len(line) >= 8:
            cx, cy = (int(x) for x in line[6:8])
        else:
            cx, cy = l + w // 2, t + h // 2  # center
        thissheet.cels[celname] = Cel(l, t, w, h, cx, cy)

    def handle_celseq(self, line):
        thissheet = self.sheets[self.cursheet]
        self.curcelseq = celseqname = line[1]
        thissheet.celseqs[celseqname] = []

    def handle_layer(self, line):
        self.curcelseq = None
        layernum = int(line[1])
        if len(line) >= 6:
            sheetname, celname, x, y = line[2:6]
            thissheet = self.sheets[sheetname]  # or raise
            if (celname not in thissheet.cels
                and celname not in thissheet.celseqs):
                raise KeyError(celname)
            flipname = line[6] if len(line) >= 7 else "none"
            flipnames[flipname]  # ensure presence
            self.layers[layernum] = Layer(
                sheetname, celname, int(x), int(y), flipname, -1
            )
        elif len(line) == 2:
            self.layers.pop(layernum, None)  # turn off layer
        else:
            raise ValueError("layer parameter count not 1 or 5")

    def handle_celseq_move(self, line):
        cmds = iter(line[1:])
        thissheet = self.sheets[self.cursheet]
        celseq = thissheet.celseqs[self.curcelseq]
        cel, x, y = None, 0, 0
        for cmd in cmds:
            if cmd == 'by':
                x += int(next(cmds))
                y += int(next(cmds))
            elif cmd in thissheet.cels:  # can't nest celseqs
                cel, step = cmd, 0
            else:
                raise KeyError(cmd)
        celseq.append(CelSeqStep(cel, x, y))

    def handle_move(self, line):
        if self.curcelseq:
            return self.handle_celseq_move(line)
        cmds = iter(line[1:])
        layernum = int(next(cmds))
        sn, cel, x, y, f, step = self.layers[layernum]
        thissheet = self.sheets[sn]
        for cmd in cmds:
            if cmd == 'flip':
                flipname = next(cmds)
                flipnames[flipname]  # ensure presence
                f = flipname
            elif cmd == 'by':
                x += int(next(cmds))
                y += int(next(cmds))
            elif cmd == 'to':
                x = int(next(cmds))
                y = int(next(cmds))
            elif cmd in thissheet.cels or cmd in thissheet.celseqs:
                cel, step = cmd, -1
            else:
                raise KeyError(cmd)
        self.layers[layernum] = Layer(sn, cel, x, y, f, step)

    def handle_skip(self, line):
        se;f.skipping = True

    def handle_noskip(self, line):
        self.skipping = False

    def handle_segment(self, line):
        self.segment_breaks.add(len(self.frames))

    def handle_wait(self, line):
        self.curcelseq = None

        # Step all cel sequences forward even if skipping rendering
        for k, thislayer in list(self.layers.items()):
            sheetname, celseqname, x, y, flipname, seqstep = thislayer
            sheetseqs = self.sheets[sheetname].celseqs
            if celseqname not in sheetseqs: continue
            celseq = sheetseqs[celseqname]
            seqstep += 1
            if seqstep >= len(celseq): seqstep = 0
            _, sx, sy = celseq[seqstep]
            x += sx
            y += sy
            self.layers[k] = thislayer._replace(x=x, y=y, seqstep=seqstep)
        celname = celseqname = None
        if self.skipping: return

        duration = int(line[1])
        slayers = sorted(self.layers.items(), reverse=True)
        im = Image.new("RGB", self.imsize, self.bgcolor)
        for _, thislayer in slayers:
            sheetname, celname, x, y, flipname, seqstep = thislayer
            thissheet = self.sheets[sheetname]
            if celname in thissheet.celseqs:
                celname = thissheet.celseqs[celname][seqstep].cel
            flipmethod, vhflags = flipnames[flipname]
            if thissheet.im.mode != 'RGBA':
                thissheet = thissheet._replace(im=thissheet.im.convert("RGBA"))
            l, t, w, h, cx, cy = thissheet.cels[celname]
            if vhflags & 1:
                cx = l + l + w - cx
            if vhflags & 2:
                cy = t + t + h - cy
            x += l - cx
            y += t - cy
            src = thissheet.im.crop((l, t, l + w, t + h))
            if flipmethod is not None:
                src = src.transpose(flipmethod)
            im.paste(src, (x, y), src)
        im = im.convert("P", dither=Image.NONE, palette=Image.ADAPTIVE)
        self.frames.append((im, duration))

    wordhandlers = {
        'size': handle_size,
        'bgcolor': handle_bgcolor,
        'sheet': handle_sheet,
        'sheetbg': handle_sheetbg,
        'cel': handle_cel,
        'celseq': handle_celseq,
        'layer': handle_layer,
        'move': handle_move,
        'skip': handle_skip,
        'noskip': handle_noskip,
        'segment': handle_segment,
        'wait': handle_wait
    }
    

def main(argv=None):
    argv = argv or sys.argv
    if len(argv) > 1 and argv[1] in ('--help', '-h', '-?', '/?'):
        print("usage: renderanim.py anim.txt out.gif")
    txtname, gifname = argv[1:3]
    
    with open(txtname, "r") as infp:
        lines = list(infp)
    job = Job()
    try:
        job.extend(lines)
    except Exception as e:
        print("%s:%d: %s" % (txtname, job.linecount, e), file=sys.stderr)
        raise
    job.save(gifname)

if __name__=='__main__':
    if 'idlelib' in sys.modules:
        main("""
./renderanim.py tilebasedwalking.txt out.ora
""".split())
    else:
        main()
