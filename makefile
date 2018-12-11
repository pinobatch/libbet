#!/usr/bin/make -f
#
# Makefile for Libbet and the Magic Floor
# Copyright 2014-2018 Damian Yerrick
#
# Copying and distribution of this file, with or without
# modification, are permitted in any medium without royalty
# provided the copyright notice and this notice are preserved.
# This file is offered as-is, without any warranty.
#

# Used in the title of the zipfile and .gb executable
title:=libbet
version:=0.03

# Space-separated list of asm files without .z80 extension
# (use a backslash to continue on the next line)
objlist := header init \
  main floorvram floormodel statusbar instructions rolling \
  fade audio pitchtable \
  ppuclear pads unpb16 rand bcd metasprite vwfdraw vwf7 popslide

ifdef COMSPEC
  ifndef GBEMU
    GBEMU := start ""
  endif
  PY := py -3
else
  ifndef GBEMU
    GBEMU := ~/.wine/drive_c/Program\ Files\ \(x86\)/bgb/bgb.exe
  endif
  PY := python3
endif

.SUFFIXES:
.PHONY: run all dist zip

run: $(title).gb
	$(GBEMU) $<
all: $(title).gb

clean:
	-rm obj/gb/*.z80 obj/gb/*.o obj/gb/*.chrgb obj/gb/*.pb16
	-rm obj/gb/*.chr1

# Packaging

dist: zip
zip: $(title)-$(version).zip

# The zipfile depends on every file in zip.in, but as a shortcut,
# mention only files on which the ROM doesn't itself depend.
$(title)-$(version).zip: zip.in $(title).gb \
  README.md CHANGES.txt obj/gb/index.txt
	$(PY) tools/zipup.py $< $(title)-$(version) -o $@
	-advzip -z3 $@

# Build zip.in from the list of files in the Git tree
zip.in: makefile
	git ls-files | grep -e "^[^.0]" > $@
	echo 05-burndown/note_from_nocash.md >> $@
	echo $(title).gb >> $@
	echo zip.in >> $@

obj/gb/index.txt: makefile
	echo "Files produced by build tools go here. (This file's existence forces the unzip tool to create this folder.)" > $@

# The ROM

objlisto = $(foreach o,$(objlist),obj/gb/$(o).o)

$(title).gb: $(objlisto)
	rgblink -p 0xFF -m$(title).map -n$(title).sym -o$@ $^
	rgbfix -p0 -v $@

obj/gb/%.o: obj/gb/%-dedent.z80 src/hardware.inc src/global.inc
	rgbasm -o $@ $<

obj/gb/%.o: obj/gb/%.z80
	rgbasm -o $@ $<

obj/gb/%-dedent.z80: src/%.z80
	$(PY) tools/bgrdedent.py -o $@ $<

# Files that will be included with incbin

obj/gb/floorvram.o: \
  obj/gb/floorpieces-h.chrgb.pb16 obj/gb/floorborder-h.chrgb.pb16
obj/gb/statusbar.o: \
  obj/gb/bigdigits-h.chr1
obj/gb/metasprite.o: \
  obj/gb/Libbet.z80
obj/gb/main.o: \
  obj/gb/Libbet.chrgb.pb16

# Graphics conversion

# .chrgb (CHR data for Game Boy) denotes the 2-bit tile format
# used by Game Boy and Game Boy Color, as well as Super NES
# mode 0 (all planes), mode 1 (third plane), and modes 4 and 5
# (second plane).
obj/gb/%.chrgb: tilesets/%.png
	rgbgfx -o $@ $<

obj/gb/%-h.chrgb: tilesets/%.png
	rgbgfx -h -o $@ $<

obj/gb/%-h.chr1: tilesets/%.png
	rgbgfx -d1 -h -o $@ $<

%.pb16: tools/pb16.py %
	$(PY) $^ $@

obj/gb/vwf7.z80: tools/vwfbuild.py tilesets/vwf7_cp144p.png
	$(PY) $^ $@

# One Make quirk that's very annoying to work around is that it's
# remotely possible for recipes with multiple outputs to fall out
# of sync.

obj/gb/Libbet.chrgb: tools/extractcels.py tilesets/Libbet.ec tilesets/Libbet.png
	$(PY) $^ $@ obj/gb/Libbet.z80

obj/gb/Libbet.z80: obj/gb/Libbet.chrgb
	touch $@

obj/gb/pitchtable.z80: tools/pitchtable.py
	$(PY) $< > $@
