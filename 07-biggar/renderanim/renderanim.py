#!/usr/bin/env python3
"""
the file format:

# establish a camera
size 160 144

# load a picture onto a layer
layer 1 filename.png

# finish this frame and wait n milliseconds
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
segment


"""
import os
import sys
import re
import argparse
from PIL import Image, ImageChops
from contextlib import closing

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

def main(argv=None):
    argv = argv or sys.argv
    if len(argv) > 1 and argv[1] in ('--help', '-h', '-?', '/?'):
        print("usage: renderanim.py anim.txt out.gif")
    txtname, gifname = argv[1:3]
    
    with open(txtname, "r") as infp:
        lines = [(i, x.strip()) for i, x in enumerate(infp)]
    lines = [
        (i, line.split())
        for i, line in lines
        if line and not line.startswith("#")
    ]

    # frame is a list of output frames
    # sheets is a dict from names to [Image, cels, filename] lists
    #     cels is a dict from celnames to
    #         (left, top, width, height, centerx, centery) tuples
    # layers is a dict from z indices to
    #     [sheetname, celname, x, y, flip] lists
    # (is there an ordered map in Python?)
    frames, sheets, layers = [], {}, {}
    curframe = cursheet = bgcolor = imw = imh = whlinenum = None
    skipping = False
    segment_breaks = {0}

    for linenum, line in lines:
        try:
            word0 = line[0]
            if word0 == 'sheet':
                cursheet, imname = line[1], " ".join(line[2:])
                im = Image.open(imname)
                sheets[cursheet] = [im, {}, imname]
            elif word0 == 'sheetbg':
                nbands = len(sheets[cursheet][0].getbands())
                if len(line) == 2 and line[1].startswith('#'):
                    color = parse_color(line1)
                else:
                    color = tuple(int(x) for x in line[1:])
                if nbands != len(line) - 1:
                    raise ValueError("expected %d bands; got %d"
                                     % (nbands, len(color)))
                if len(color) == 1: color = color[0]
                sheets[cursheet][0].info["transparency"] = color
            elif word0 == 'cel':
                celname = line[1]
                if len(line) >= 6:
                    l, t, w, h = (int(x) for x in line[2:6])
                else:
                    w, h = sheets[cursheet][0].size
                    l = t = 0
                if len(line) >= 8:
                    cx, cy = (int(x) for x in line[6:8])
                else:
                    cx, cy = l + w // 2, t + h // 2  # center
                sheets[cursheet][1][celname] = l, t, w, h, cx, cy
            elif word0 == 'size':
                if whlinenum is None:
                    imw, imh = (int(x) for x in line[1:3])
                    whlinenum = linenum
                else:
                    raise ValueError("size already set on line %d"
                                     % (whlinenum + 1))
            elif word0 == 'bgcolor':
                if len(line) >= 2:
                    bgcolor = parse_color(line[1])
                else:
                    bgcolor = None
            elif word0 == 'layer':
                layernum = int(line[1])
                if len(line) >= 6:
                    sheetname, celname, x, y = line[2:6]
                    if sheetname not in sheets:
                        raise KeyError(sheetname)
                    if celname not in sheets[sheetname][1]:
                        raise KeyError(celname)
                    flipname = line[6] if len(line) >= 7 else "none"
                    flipnames[flipname]  # ensure presence
                    layers[layernum] = [
                        sheetname, celname, int(x), int(y), flipname
                    ]
                elif len(line) == 2:
                    layers.pop(layernum, None)  # turn off layer
                else:
                    raise ValueError("layer parameter count not 1 or 5")
            elif word0 == 'move':
                layernum = int(line[1])
                thislayer = layers[layernum]
                cmds = iter(line[2:])
                for cmd in cmds:
                    if cmd == 'flip':
                        flipname = next(cmds)
                        flipnames[flipname]  # ensure presence
                        thislayer[4] = flipname
                    elif cmd == 'by':
                        dx = int(next(cmds))
                        dy = int(next(cmds))
                        thislayer[2] += dx
                        thislayer[3] += dy
                    elif cmd == 'to':
                        x = int(next(cmds))
                        y = int(next(cmds))
                        thislayer[2] = x
                        thislayer[3] = y
                    elif cmd in sheets[thislayer[0]][1]:
                        thislayer[1] = cmd
                    else:
                        raise KeyError(cmd)
            elif word0 == 'skip':
                skipping = True
            elif word0 == 'noskip':
                skipping = False
            elif word0 == 'segment':
                segment_breaks.add(len(frames))
            elif word0 == 'wait':
                if skipping: continue
                duration = int(line[1])
                slayers = sorted(layers.items(), reverse=True)
                im = Image.new("RGB", (imw, imh), bgcolor)
                for _, thislayer in slayers:
                    sheetname, celname, x, y, flipname = thislayer
                    flipmethod, vhflags = flipnames[flipname]
                    thissheet = sheets[sheetname]
                    if thissheet[0].mode != 'RGBA':
                        thissheet[0] = thissheet[0].convert("RGBA")
                    l, t, w, h, cx, cy = thissheet[1][celname]
                    if vhflags & 1:
                        cx = l + l + w - cx
                    if vhflags & 2:
                        cy = t + t + h - cy
                    x += l - cx
                    y += t - cy
                    src = thissheet[0].crop((l, t, l + w, t + h))
                    if flipmethod is not None:
                        src = src.transpose(flipmethod)
                    im.paste(src, (x, y), src)
                im = im.convert("P", dither=Image.NONE, palette=Image.ADAPTIVE)
                frames.append((im, duration))
                im = None
            else:
                raise ValueError("unrecognized keyword %s" % word0)
        except Exception as e:
            print("Exception on line %d" % (linenum + 1))
            raise

    segment_breaks.add(len(frames))
    segment_breaks = sorted(segment_breaks)
    namepart, extpart = os.path.splitext(gifname)
    for s, e in zip(segment_breaks, segment_breaks[1:]):
        if len(segment_breaks) > 2:
            outfilename = "%s_%d%s" % (namepart, s, extpart)
            print("%s: writing %s" % (txtname, outfilename))
        else:
            outfilename = gifname
        extlower = extpart.lower()
        if extlower == '.gif':
            first_cel = frames[s][0]
            subsequent_cels = [f[0] for f in frames[s + 1:e]]
            cel_durations = [f[1] for f in frames[s:e]]
            first_cel.save(
                outfilename,
                save_all=True,  # make animation
                append_images=subsequent_cels,  # frames after first
                duration=cel_durations,  # in milliseconds
                loop=0
            )
        elif extlower == '.ora':
            filedata = make_ora_from_frames(frames[s:e])
            with open(outfilename, "wb") as outfp:
                outfp.write(filedata)
        else:
            raise ValueError("unknown extension %s" % extpart)

if __name__=='__main__':
    if 'idlelib' in sys.modules:
        main("""
./renderanim.py anim.txt ../../renders/renderanim-out.ora
""".split())
    else:
        main()
