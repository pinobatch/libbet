;
; Basic SMS/GG VDP interfacing routines
;
; Copyright 2019 Damian Yerrick
; 
; This software is provided 'as-is', without any express or implied
; warranty.  In no event will the authors be held liable for any damages
; arising from the use of this software.
; 
; Permission is granted to anyone to use this software for any purpose,
; including commercial applications, and to alter it and redistribute it
; freely, subject to the following restrictions:
; 
; 1. The origin of this software must not be misrepresented; you must not
;    claim that you wrote the original software. If you use this software
;    in a product, an acknowledgment in the product documentation would be
;    appreciated but is not required.
; 2. Altered source versions must be plainly marked as such, and must not be
;    misrepresented as being the original software.
; 3. This notice may not be removed or altered from any source distribution.
;

.include "src/sms.inc"

.bank 0
.section "ppuclear" free

;;
; Waits for the vblank handler to increase the variable nmis
wait_vblank_irq:
  ; Unlike Game Boy (DI HALT) and WDC 65816 (SEI WAI), Zilog Z80
  ; doesn't support waiting for the next interrupt without calling
  ; its handler.
  ei
  ld hl, nmis
  ld a, (hl)
  @loop:
    halt
    cp (hl)
    jr z, @loop
  ret

;;
; Sets the VDP control port to HL
vdp_seek_hl:
  ld a, l
  out (VDPCTRL),a
  ld a, h
  out (VDPCTRL),a
  ret

;;
; Clears the nametable to tile 0.
vdp_clear_nt:
  vdp_seek_xy 0, 0
  ld d, 32*28*2/256
  xor a           ; A: byte value (0)
  ; fall through to vmemset_256d

;;
; Clears 256*D pages of VRAM to A.
vmemset_256d:
  ld b, 0
  @loop:
    out (VDPDATA),a   ; Output to VRAM address and increment it
    djnz @loop
    dec d       ; Proceed to next page
    jp nz, @loop
  ret

;;
; Clears all sprites from shadow SAT and pushes shadow SAT to VRAM
vdp_clear_sat:
  ld hl, sat_used
  ld [hl], $40
  ; fall through to push_sat

;;
; Copies the sprite attribute table to VRAM.
; It's not quite as fast as OAM DMA on NES or GB, but it'll do
vdp_push_sat:
  ; Terminate sprite attribute table
  ld hl, sat_used
  ld l, [hl]
  ld h, >sat_y
  ld [hl], $D0

  ; Push Y coordinates to SAT at $7F00
  ld hl, sat_y
  ld bc, NUM_SPRITES*256+VDPDATA
  xor a
  out (VDPCTRL), a
  ld a, $7F
  out (VDPCTRL), a
  otir

  ; Push X and N coordinates to $7F80
  inc a  ; $80
  out (VDPCTRL), a
  dec a  ; $7F
  out (VDPCTRL), a
  ld b, NUM_SPRITES*2
  otir
  ret

.ends

; Tile flipping and expansion ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

.section "load_4bpp" free
;;
; Loads 4bpp tile data to VRAM with optional bitplane transformation.
; 4bpp version: 137 cycles/sliver
; A 16x32 sprite cel like Mario is 64 slivers or 8768 lines
; A scanline is 228 cycles, so this is 39 lines
; @param HL source
; @param B sliver count (width*height/8, or data size/4)
; @param D high byte of pointer to transformation (identity, bit
; reverse table, or scale) table
load_4bpp_cel:
  ld e, [hl]        ; 7
  inc hl            ; 6
  ld a, [de]        ; 7
  out (VDPDATA), a  ; 11
  ld e, [hl]        ; 7
  inc hl            ; 6
  ld a, [de]        ; 7
  out (VDPDATA), a  ; 11
  ld e, [hl]        ; 7
  inc hl            ; 6
  ld a, [de]        ; 7
  out (VDPDATA), a  ; 11
  ld e, [hl]        ; 7
  inc hl            ; 6
  ld a, [de]        ; 7
  out (VDPDATA), a  ; 11
  djnz load_4bpp_cel; 13
  ret

;;
; 2bpp to 4bpp expansion and optional flipping: 129 cycles/sliver
; A 16x32 sprite cel is 8256 or 37 lines.
; 
; @param HL source
; @param B sliver count (width*height/8, or data size/4)
; @param D high byte of pointer to transformation (identity, bit
; reverse table, or scale) table
; @param IX subpalette choice. $0000: use colors 0, 1, 2, 3;
; $00FF: 0, 5, 6, 7; $FF00: 0, 9, 10, 11; $FFFF: 0, 13, 14, 15.
; To use 0, 4, 8, 12: Set VRAM address to $4002+n*32.
load_2bpp_cel:
  ld e, [hl]        ; 7
  ld a, [de]        ; 7
  out (VDPDATA), a  ; 11
  inc hl            ; 6
  ld c, a           ; 4
  ld e, [hl]        ; 7
  ; peak register pressure is here:
  ; HL: src ptr; DE: next flip byte; C: plane 0; B: count;
  ; A: must be open to retrieve plane 1
  ; Thus we need IX for 2bpp to 4bpp expansion
  ld a, [de]        ; 7
  out (VDPDATA), a  ; 11
  or c              ; 4

  ; A holds 1 for opaque pixels in this sliver and 0 for transparent
  ; pixels.  Use this to write planes 2-3 so as to select colors
  ; 5-7, 9-11, or 13-15.
  ; The minimum out-to-out time of this routine is 27 cycles.
  ; Sega documents allegedly recommend 29 cycles, but sverx claims
  ; that hardware tests show 26 cycles are fine.
  ; https://www.smspower.org/forums/post108712#108712
  ; Though the fetch pattern implies a slot every 32 pixels or 21.3
  ; cycles, there appears to be 4 cycles of PPU-internal overhead
  ; to prepare the slot.
  ; https://www.smspower.org/forums/16485-GenesisMode4VRAMTiming
  ld c, a           ; 4
  and ixl           ; 8
  out (VDPDATA), a  ; 11
  inc hl            ; 6  - increment HL here to let the VDP process the write
  ld a, c           ; 4
  and ixh           ; 8
  out (VDPDATA), a  ; 11
  djnz load_2bpp_cel; 13
  ret

;;
; Unpacks a font to 4bpp data using colors 0 and 1 during blanking.
; To use colors 0 and 2, 0 and 4, or 0 and 8, set the VRAM address
; to $4001-$4003+n*2.
; @param HL pointer to font data
; @param D size of font data in 256-byte (32-tile) units
load_1bpp_font:
  ld bc,VDPDATA         ; B: counter within group C: output port
  xor a  ; A will contain 0 throughout
  WriteTilesLoop:
    outi        ; Output 1 data byte and move HL to next data byte
    out (c), a  ; then three zero bytes to tell the VDP to use
    out (c), a  ; colors 0 and 1.  Don't need to spin because
    out (c), a  ; font loading happens with the screen off.
    jr nz, WriteTilesLoop
    dec d       ; Move to next group of 32 tiles
    jr nz, WriteTilesLoop
  ret
.ends


.section "idtable" align 256 free
identity_table:
  .repeat 256 index I
    .db I
  .endr
hflip_table:
  .repeat 256 index I
    .db ((I&$80)>>7)|((I&$40)>>5)|((I&$20)>>3)|((I&$10)>>1)|((I&$08)<<1)|((I&$04)<<3)|((I&$02)<<5)|((I&$01)<<7)
  .endr
.ends

