#!/usr/bin/make -f
# Makefile for Sega Master System 32K project template

title:=hopesup
version:=wip
objlist:= \
  init main statusbar floorvram floormodel \
  bcd ppuclear pads vwfdraw vwf7_cp144p

objdir:=obj/something
srcdir:=src
imgdir:=tilesets

EMU := /opt/blastem/blastem
EMU2 := ../../meka/meka/meka
CC := gcc-8
CFLAGS := -Wall -Wextra -Os

# Optionally recompress the zipfile.
# If AdvanceCOMP is installed: advzip -z3
# Otherwise skip it:           true
REZIP := advzip -z3

# Executable names differ between Windows and *n?x
ifdef COMSPEC
DOTEXE:=.exe
PY:=py
else
DOTEXE:=
PY:=python3
endif
PNGTO := ../tools/pilbmp2nes.py

# Convenience targets
.PHONY: run runalt rungg all clean dist zip tools
.SUFFIXES:

run: $(title).sms
	$(EMU) $<
runalt: $(title).sms
	$(EMU2) $<

all: $(title).sms

dist: zip

zip: $(title)-$(version).zip

# Graphics conversion and compression

$(objdir)/%.4b: $(PNGTO) $(imgdir)/%.png
	$(PY) $^ -o $@ --planes '0,1,2,3' -H24
$(objdir)/%1616.2b: $(PNGTO) $(imgdir)/%.png
	$(PY) $^ -o $@ --planes '0,1' -W16 -H16
$(objdir)/%.2b: $(PNGTO) $(imgdir)/%.png
	$(PY) $^ -o $@ --planes '0,1'
$(objdir)/%.1b: $(PNGTO) $(imgdir)/%.png
	$(PY) $^ -o $@ --planes '0'
$(objdir)/%.pb16: tools/pb16.py $(objdir)/%
	$(PY) $^ $@
$(objdir)/%.iu: tools/incruniq.py $(objdir)/%.2b
	$(PY) $^ $@
$(objdir)/vwf7_cp144p.asm: tools/vwfbuild.py ../tilesets/vwf7_cp144p.png
	$(PY) $^ $@

# LUT generation

$(objdir)/pitchtable.asm: tools/pitchtable.py
	$(PY) $< > $@

# Assembly

$(objdir)/%.o: $(srcdir)/%.asm $(srcdir)/sms.inc
	wla-z80 -o $@ $<
$(objdir)/%.o: $(objdir)/%.asm $(srcdir)/sms.inc
	wla-z80 -o $@ $<
$(objdir)/%-gg.o: $(srcdir)/%.asm $(srcdir)/sms.inc
	wla-z80 -D GAMEGEAR=1 -o $@ $<
$(objdir)/%-gg.o: $(objdir)/%.asm $(srcdir)/sms.inc
	wla-z80 -D GAMEGEAR=1 -o $@ $<

# Additional deps (.include/.incbin)

$(objdir)/statusbar.o: \
  $(objdir)/16x16digits1616.2b

# Linking

objlistsms := $(foreach o,$(objlist),$(objdir)/$(o).o)
objlistgg := $(foreach o,$(objlist),$(objdir)/$(o)-gg.o)

$(objdir)/objlist: makefile
	echo [objects] > $@
	for f in $(objlistsms) ; do echo $$f >> $@; done

$(title).sms: $(objdir)/objlist $(objlistsms)
	wlalink -d -r -v -s $< $@

# Packaging

$(objdir)/index.txt: makefile
	echo Meow. > $@

$(title)-$(version).zip: \
  zip.in all README.md CHANGES.txt $(objdir)/index.txt
	zip -9 -u $@ -@ < $<
	$(REZIP) $@

clean:
	-rm $(objdir)/*.o $(objdir)/objlist $(objdir)/objlist-gg $(title).sym
	-rm $(objdir)/*.pb16 $(objdir)/*.iu $(objdir)/*.?b $(objdir)/*.asm
