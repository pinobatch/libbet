#!/usr/bin/env python3
# Copr, 2019 Damian Yerrick
# insert zlib license here
import os
import sys
sys.path.append(os.path.join(os.path.dirname(sys.argv[0]), "../tools"))
from uniq import uniq
import pb16

class BitByteInterleave(object):
    def __init__(self):
        self.out = bytearray(1)
        self.bitsindex, self.bitsleft = 0, 8

    def putbyte(self, c):
        self.out.append(c)

    def putbytes(self, c):
        self.out.extend(c)

    def putbits(self, value, length=1):
        while length > 0:
            # Make room for at least 1 more bit
            if self.bitsleft == 0:
                self.bitsindex, self.bitsleft = len(self.out), 8
                self.out.append(0)

            # How much of this value can we pack?
            value &= (1 << length) - 1
            length -= self.bitsleft
            if length >= 0:
                self.bitsleft = 0  # squeeze as many bits as we can
                self.out[self.bitsindex] |= value >> length
            else:
                self.bitsleft = -length  # space left for more bits
                self.out[self.bitsindex] |= value << -length

    def __len__(self):
        return len(self.out)

    def __bytes__(self):
        return bytes(self.out)

    def __iter__(self):
        return iter(self.out)

def iur_encode(chrdata, *, report=False):
    """Test experimental IUR tilemap codec"""

    utiles, tilemap = uniq(chrdata)

    # Test type stickiness (brand new uniques vs. horizontal runs)
    lastwasnew, lastbyte, maxsofar = False, 0, 0
    newnew = oldmatches = matchafternew = newafternonnew = diffold = 0
    out = BitByteInterleave()
    for t in tilemap:
        isnew = t > maxsofar
        eqlast = t == lastbyte
        ismatch = isnew if lastwasnew else eqlast
        if ismatch:
            # 0: Same run type as last time
            out.putbits(0)
            if isnew:
                newnew += 1
            else:
                oldmatches += 1
        elif isnew:
            # 10: Switch run type from non-new to new
            out.putbits(0b10, 2)
            newafternonnew += 1
        elif eqlast:
            # 10: Switch run type from new to non-new
            out.putbits(0b10, 2)
            matchafternew += 1
        else:
            # 11: Literal byte follows
            out.putbits(0b11, 2)
            out.putbyte(t)
            diffold += 1
        lastbyte, lastwasnew = t, isnew
        maxsofar = max(t, maxsofar)

    if report:
        pbunique = b''.join(pb16.pb16(b''.join(utiles)))
        sameas1ago = [l for l, r in zip(tilemap, tilemap[1:]) if l == r]
        sameas2ago = [l for l, r in zip(tilemap, tilemap[2:]) if l == r]
        sameaslplus1 = [l for l, r in zip(tilemap, tilemap[1:]) if l + 1 == r]
        print("%d map entries match left; %d match 2 to the left; %d match left + 1"
              % (len(sameas1ago), len(sameas2ago), len(sameaslplus1)))

        mapbits = (newnew + oldmatches
                   + 2 * matchafternew + 2 * newafternonnew
               + 10 * diffold)
        mapbytes = -(-mapbits // 8)
        line = ("mapsz=%d utiles=%3d nn=%3d om=%3d man=%3d nao=%3d do=%3d bits=%4d"
                % (len(chrdata), len(utiles),
                   newnew, oldmatches, matchafternew,
                   newafternonnew, diffold, mapbits))
        print(line)
        print("%d bytes tiles, %d bytes map, %d bytes total"
              % (len(pbunique), mapbytes, len(pbunique) + mapbytes))
        assert len(out) == mapbytes

    return bytes(out)

def test_iur():
    from PIL import Image
    from pilbmp2nes import pilbmp2chr, formatTilePlanar

    gbformat = lambda tile: formatTilePlanar(tile, "0,1")
    test_filenames = [
        ("Proposed MF title screen",
         "../renders/title_bgonly.png"),
        ("Green Hill Zone for GB",
         "../../240p-test-mini/gameboy/tilesets/greenhillzone.png"),
        ("Gus portrait for DMG",
         "../../240p-test-mini/gameboy/tilesets/Gus_portrait.png"),
        ("Linearity quadrant for GB",
         "../../240p-test-mini/gameboy/tilesets/linearity-quadrant.png"),
        ("Sharpness for GB",
         "../../240p-test-mini/gameboy/tilesets/sharpness.png"),
        ("Stopwatch face for GB",
         "../../240p-test-mini/gameboy/tilesets/stopwatchface.png"),
    ]
    for title, filename in test_filenames:
        print("Stats for %s (%s)" % (title, os.path.basename(filename)))
        im = Image.open(filename)
        chrdata = pilbmp2chr(im, formatTile=gbformat)
        iur_encode(chrdata, report=True)
        print()

if __name__=='__main__':
    test_iur()
