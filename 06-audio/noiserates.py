#!/usr/bin/env python3
"""
Game Boy noise sample rates for each value of NR43, and the closest
NR43 to each NES noise sample rate

Expected output:

gb $00,524288 Hz
gb $01,262144 Hz
gb $02,131072 Hz
gb $03, 87381 Hz
gb $04, 65536 Hz
gb $05, 52429 Hz
gb $06, 43691 Hz
gb $07, 37449 Hz
gb $14, 32768 Hz
gb $15, 26214 Hz
gb $16, 21845 Hz
gb $17, 18725 Hz
gb $24, 16384 Hz
gb $25, 13107 Hz
gb $26, 10923 Hz
gb $27,  9362 Hz
gb $34,  8192 Hz
gb $35,  6554 Hz
gb $36,  5461 Hz
gb $37,  4681 Hz
gb $44,  4096 Hz
gb $45,  3277 Hz
gb $46,  2731 Hz
gb $47,  2341 Hz
gb $54,  2048 Hz
gb $55,  1638 Hz
gb $56,  1365 Hz
gb $57,  1170 Hz
gb $64,  1024 Hz
gb $65,   819 Hz
gb $66,   683 Hz
gb $67,   585 Hz
gb $74,   512 Hz
gb $75,   410 Hz
gb $76,   341 Hz
gb $77,   293 Hz
nes $0,447443 Hz = gb $00,524288 Hz;17% diff
nes $1,223722 Hz = gb $01,262144 Hz;17% diff
nes $2,111861 Hz = gb $02,131072 Hz;17% diff
nes $3, 55930 Hz = gb $05, 52429 Hz; 6% diff
nes $4, 27965 Hz = gb $15, 26214 Hz; 6% diff
nes $5, 18643 Hz = gb $17, 18725 Hz; 0% diff
nes $6, 13983 Hz = gb $25, 13107 Hz; 6% diff
nes $7, 11186 Hz = gb $26, 10923 Hz; 2% diff
nes $8,  8860 Hz = gb $27,  9362 Hz; 6% diff
nes $9,  7046 Hz = gb $35,  6554 Hz; 7% diff
nes $a,  4710 Hz = gb $37,  4681 Hz; 1% diff
nes $b,  3523 Hz = gb $45,  3277 Hz; 7% diff
nes $c,  2349 Hz = gb $47,  2341 Hz; 0% diff
nes $d,  1762 Hz = gb $55,  1638 Hz; 7% diff
nes $e,   880 Hz = gb $65,   819 Hz; 7% diff
nes $f,   440 Hz = gb $75,   410 Hz; 7% diff

"""

def gbnoiserate(x):
    "Convert a Game Boy NR43 value to a sample rate in Hz"
    freq = 524288 >> (x >> 4)
    divisor = (x & 0x07) * 2 or 1
    return freq/divisor

# This table helps it generate only unique rates: 00-07, 14-17,
# 24-27, etc.  Pairs like 46 and 53 sound the same, as do sets
# like 24, 32, 41, and 50.  Though the table could be extended
# to D4, 74 is adequate to cover the NES's entire range.
# Incidentally, for Sega Master System and Game Gear noise,
# you just need 35, 45, and 55.
hinibbles = [0x00,0x04,0x14,0x24,0x34,0x44,0x54,0x64,0x74]

# NES noise period table and respective best GB approximations
nesperiods = [
  4,8,16,32, 64,96,128,160,
  202,254,380,508, 762,1016,2034,4068
]
nr43s = [
    0x00,0x01,0x02,0x05, 0x15,0x17,0x25,0x26,
    0x27,0x35,0x37,0x45, 0x47,0x55,0x65,0x75
]
for hinib in hinibbles:
    for nr43 in range(hinib, hinib+4):
        gbf = int(round(gbnoiserate(nr43)))
        print("gb $%02x,%6d Hz" % (nr43, gbf))

for i, (fcp, nr43) in enumerate(zip(nesperiods, nr43s)):
    fcf = int(round(1789773/fcp))
    gbf = int(round(gbnoiserate(nr43)))
    pctdiff = int(round(abs(1 - (gbf/fcf)) * 100))
    print("nes $%x,%6d Hz = gb $%02x,%6d Hz;%2d%% diff"
          % (i, fcf, nr43, gbf, pctdiff))
