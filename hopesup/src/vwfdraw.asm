.include "src/sms.inc"

.def lineImgBufLen 128
.def CHAR_BIT 8
.def LOG_GLYPH_HEIGHT 3
.def GLYPH_HEIGHT (1 << LOG_GLYPH_HEIGHT)
.def GLYPH_HEIGHT_MINUS_1 7

.ramsection "lineImgBuf" bank 0 slot WRAM0 align 256
lineImgBuf ds lineImgBufLen
.ends

.ramsection "vwflocals" bank 0 slot WRAM0
Lshiftermask ds 1
Ldstoffset ds 1
.ends

.bank 0 slot 0

.section "vwfPutTile" align GLYPH_HEIGHT
not_ff_shr_x: .db $00,$80,$C0,$E0,$F0,$F8,$FC,$FE

; The second half of the routine comes before the first half to ease alignment
vwfPutTile_shifter:
  .repeat GLYPH_HEIGHT_MINUS_1
    rrca
  .endr
  ld h,a  ; H: all glyph bits, circularly rotated

  ; Load destination address
  ld a,[Ldstoffset]
  ld l,a

  ; Break it up into 2 bytes
  ld a,[Lshiftermask]
  and h
  ld c,a  ; C: right half bits
  xor h   ; A: left half bits

  ; OR in the left byte
  ld h,>(lineImgBuf)
  or [hl]
  ld [hl],a

  ; OR in the left
  ld a,l
  add GLYPH_HEIGHT
  ld l,a
  ld a,[hl]
  or c
  ld [hl],a
  ld a,l
  sub GLYPH_HEIGHT-1
vwfPutTile_have_dstoffset:
  ld [Ldstoffset],a

  ; Advance to next row
  and GLYPH_HEIGHT-1
  ret z

  ; Shift each row
vwfPutTile_rowloop:
  ; Read an 8x1 sliver of the glyph into A
  ld a,[de]
  inc e
  or a
  jr z,@sliver_is_blank

  ; Shift the sliver
  ld h,>(vwfPutTile_shifter)
  ld l,b
  jp hl

  ; Fast path handling for blank slivers
@sliver_is_blank:
  ld a,[Ldstoffset]
  inc a
  jr vwfPutTile_have_dstoffset

;;
; Draws the tile for glyph A at horizontal position B
vwfPutTile:

  ; Calculate address of glyph
  ld h,0
  ld l,a
  ld de,vwfChrData - (' '*GLYPH_HEIGHT)
  .repeat LOG_GLYPH_HEIGHT
    add hl,hl
  .endr
  add hl,de

  ; Get the destination offset in line buffer
  ld a,b
  .if LOG_GLYPH_HEIGHT > 3
    .repeat LOG_GLYPH_HEIGHT-3
      rlca
    .endr
  .endif
  and $100-GLYPH_HEIGHT
  ld [Ldstoffset],a

  ; Get the mask of which bits go here and which to the next tile
  xor b
  ld e,a  ; E = horizontal offset within tile
  ld bc,not_ff_shr_x
  add c
  ld c,a  ; BC = ff_shr_x+horizontal offset
  ld a,[bc]
  ld [Lshiftermask],a

  ; Calculate the address of the shift routine
  ld a,<(vwfPutTile_shifter) + CHAR_BIT - 1
  sub e
  ld b,a  ; B: which shifter to use

  ld d,h
  ld e,l
  jr vwfPutTile_rowloop


;;
; Write glyphs for the 8-bit-encoded characters string at (hl) to
; X position B in the VWF buffer
; @return HL pointer to the first character not drawn
vwfPuts:
@chloop:
  ; Load character, stopping at control character
  ld a,[hl]
  inc hl
  cp 32
  jr c,@decret

  ; Save position, draw glyph, load position
  jr z,@nodrawspace
  ld c,a
  push hl
  push bc
  call vwfPutTile
  pop bc
  pop hl
  ld a,c
@nodrawspace:
  
  ; Add up the width of the glyph
  ld de,vwfChrWidths-' '
  add e
  ld e,a
  jr nc,@gwnowrap
  inc d
@gwnowrap:
  ld a,[de]
  add b
  ld b,a

  cp lineImgBufLen
  jr c,@chloop
  ret

; Return points HL at the first undrawn character
@decret:
  dec hl
  ret

;;
; Clears the line image.
; @return B = 0; HL = lineImgBuf + lineImgBufLen
vwfClearBuf:
  ld hl,lineImgBuf
  ld b,lineImgBufLen
  xor a
.loop:
  ld [hl],a
  inc l
  djnz .loop
  ret

.ends