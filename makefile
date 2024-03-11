#!/usr/bin/make -f
#
# Makefile for Libbet and the Magic Floor
# Copyright 2014-2020 Damian Yerrick
#
# Copying and distribution of this file, with or without
# modification, are permitted in any medium without royalty
# provided the copyright notice and this notice are preserved.
# This file is offered as-is, without any warranty.
#

# Used in the title of the zipfile and .gb executable
title:=libbet
version:=0.08

# Space-separated list of asm files without .z80 extension
# (use a backslash to continue on the next line)
objlist := header init localvars \
  main floormodel \
  rolling prevcombo \
  instructions debrief achievements intro \
  statusbar floorvram fade audio pitchtable \
  ppuclear pads unpb16 rand bcd metasprite vwfdraw vwf7 \
  popslide sgb

ifdef COMSPEC
  ifndef GBEMU
    GBEMU := start ""
  endif
  PY := py -3
else
  ifndef GBEMU
    # I now use a shell script in ~/.local/bin
    GBEMU := bgb
  endif
  PY := python3
endif

# Support out-of-PATH RGBDS
RGBASM  := $(RGBDS)rgbasm
RGBLINK := $(RGBDS)rgblink
RGBGFX  := $(RGBDS)rgbgfx
RGBFIX  := $(RGBDS)rgbfix

.SUFFIXES:
.PHONY: run all dist zip

run: $(title).gb
	$(GBEMU) $<
all: $(title).gb

clean:
	-rm obj/gb/*.z80 obj/gb/*.o obj/gb/*.2bpp obj/gb/*.pb16
	-rm obj/gb/*.chr1

# Packaging

dist: zip
zip: $(title)-$(version).zip

# The zipfile depends on every file in zip.in, but as a shortcut,
# mention only files on which the ROM doesn't itself depend.
$(title)-$(version).zip: zip.in makefile $(title).gb \
  README.md CHANGES.txt obj/gb/index.txt
	$(PY) tools/zipup.py $< $(title)-$(version) -o $@
	-advzip -z3 $@

# Build zip.in from the list of files in the Git tree
zip.in: makefile
	git ls-files | grep -e "^[^.0]" | grep -v "^hopesup" > $@
	echo 05-burndown/note_from_nocash.md >> $@
	echo $(title).gb >> $@
	echo zip.in >> $@

obj/gb/index.txt: makefile
	echo "Files produced by build tools go here. (This file's existence forces the unzip tool to create this folder.)" > $@

# The ROM

objlisto = $(foreach o,$(objlist),obj/gb/$(o).o)

$(title).gb: $(objlisto)
	$(RGBLINK) -p 0xFF -m$(title).map -n$(title).sym -o$@ $^
	$(PY) tools/beforefix.py $@
	$(RGBFIX) -jvsc -k "OK" -l 0x33 -m ROM -p 0xFF -t "LIBBET" -v $@

obj/gb/%.o: src/%.z80 src/hardware.inc src/global.inc
	${RGBASM} -h -o $@ $<

obj/gb/%.o: obj/gb/%.z80
	${RGBASM} -h -o $@ $<

# Files that will be included with incbin

obj/gb/intro.o: \
  obj/gb/roll32-h.2bpp.pb16
obj/gb/floorvram.o: \
  obj/gb/floorpieces-h.2bpp.pb16 \
  obj/gb/floorborder-h.2bpp.pb16 obj/gb/floorborder-sgb-h.2bpp.pb16
obj/gb/statusbar.o: \
  obj/gb/bigdigits-h.chr1
obj/gb/metasprite.o: \
  obj/gb/Libbet.z80
obj/gb/main.o: \
  obj/gb/Libbet.2bpp.pb16
obj/gb/sgb.o: \
  obj/gb/sgbborder.border

# Local variable allocation

obj/gb/localvars.z80: tools/savescan.py $(wildcard src/*.z80)
	$(PY) $^ -o $@

# Graphics conversion

# .2bpp (CHR data for Game Boy) denotes the 2-bit tile format
# used by Game Boy and Game Boy Color, as well as Super NES
# mode 0 (all planes), mode 1 (third plane), and modes 4 and 5
# (second plane).
obj/gb/%.2bpp: tilesets/%.png
	${RGBGFX} -o $@ $<

obj/gb/%-h.2bpp: tilesets/%.png
	${RGBGFX} -Z -o $@ $<

obj/gb/%-h.chr1: tilesets/%.png
	${RGBGFX} -d1 -Z -o $@ $<

%.pb16: tools/pb16.py %
	$(PY) $^ $@

obj/gb/vwf7.z80: tools/vwfbuild.py tilesets/vwf7_cp144p.png
	$(PY) $^ $@

# One quirk of Make pre-4.3 that's annoying to work around is that
# recipes with multiple outputs may fall out of sync.

obj/gb/Libbet.2bpp: tools/extractcels.py tilesets/Libbet.ec tilesets/Libbet.png
	$(PY) $^ $@ obj/gb/Libbet.z80

obj/gb/Libbet.z80: obj/gb/Libbet.2bpp
	touch $@

obj/gb/pitchtable.z80: tools/pitchtable.py
	$(PY) $< > $@

obj/gb/%.border: tools/makeborder.py tilesets/%.png
	$(PY) $^ $@

