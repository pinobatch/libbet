.include "src/sms.inc"

.def STATUS_FIRST_TILE $C0
.def STATUS_BIG_DIGITS $C0
.def STATUS_BLANK_TILE $EC
.def STATUS_SLASH_TILE $EE
.def STATUS_M_TILE $EF
.def STATUS_SMALL_DIGITS $F0

.section "statuschr" free
digits_chr:
.incbin "obj/something/16x16digits1616.2b"
.ends

.section "statusbar" free

load_status_chr:
  vdp_seek_tile $C0
  ld hl, digits_chr
  ld b, 0
  ld d, >identity_table
  ld ix, 0
  call load_2bpp_cel
  call load_2bpp_cel

  ; TODO: Color the status bar
  ret

init_status_bar:
  ld hl, debughex0
  ld [hl], $C0
  inc hl
  ld [hl], $DE

  ; Set background
  vdp_seek_xy 0, 22
  ld b, 64
  @clrloop:
    ld a, STATUS_BLANK_TILE
    out [VDPDATA], a
    xor a
    out [VDPDATA], a
    djnz @clrloop

  ; Write "Combo"
  vdp_seek_xy 6, 23
  ld a, $C0
  call put2digsm
  ld a, STATUS_M_TILE
  call put1tileid
  ld a, $B0
  call put2digsm

  ; Percent sign
  ld l, <(18 * 2 + 22 * 64)
  ld a, 10
  call put1digbig
  
  ld a, 69
  ld [max_score], a
  ld a, 5
  ld [cur_combo], a
  ld a, 6
  ld [cur_score], a

  ; Write level maximum score
  vdp_seek_xy 27, 23
  ld a, STATUS_SLASH_TILE
  call put1tileid
  ld a, [max_score]
  call bcd8bit_baa
  call put2digsm

update_status_bar:

  ld a, [max_score]
  ld c, a
  ld a, [cur_score]
  cp c
  jr c, @not_100pct
    ld l, <(12 * 2 + 22 * 64)
    ld a, $10
    call put2digbig
    xor a
    jr @have_last_pctdigit
  @not_100pct:
    ld b, a
    call pctdigit
    ld l, <(14 * 2 + 22 * 64)
    or a
    jr nz, @atleast10pct
      ld a, 11
    @atleast10pct:
    call put1digbig
    call pctdigit
  @have_last_pctdigit:
  call put1digbig

  ld l, <(2 * 2 + 22 * 64)
  ld a, 5
  call put2decdigbig
  ld l, <(23 * 2 + 22 * 64)
  ld a, 15
put2decdigbig:
  call bcd8bit_baa
put2digbig:
  ld c, a
  and $F0
  jr nz, @yes_tens
    ld a, 11
    jr @have_tens_digit
  @yes_tens:
    ld a, c
    and $F0
    rrca
    rrca
    rrca
    rrca
  @have_tens_digit:
  call put1digbig
  ld a, c
  and $0F
put1digbig:
  ; may trash ABDEH, must add 2 to L
  add a
  add a
  or STATUS_BIG_DIGITS
  ld h, a

  ld a, l  ; Top row
  call @puttileb
  ld a, l  ; Bottomrow
  inc l
  inc l
  inc l
  inc l
  add 64
@puttileb:
  out [VDPCTRL], a
  ld a, $7D
  out [VDPCTRL], a
  ld a, h
  out [VDPDATA], a
  cp STATUS_BLANK_TILE
  ld a, 0
  nop
  out [VDPDATA], a
  nop
  jr nc, @isblank1
    inc h
  @isblank1:
  ld a, h
  out [VDPDATA], a
  ld a, 0
  jr nc, @isblank2
    inc h
  @isblank2:
  out [VDPDATA], a
  ret
.ends

draw_debughex:
  vdp_seek_xy 7, 22
  ld a, [debughex0]
  call put2digsm
  ld a, [debughex1]
put2digsm:
  push af
  rrca
  rrca
  rrca
  rrca
  call put1dig
  pop af
put1dig:
  or STATUS_SMALL_DIGITS
put1tileid:
  out [VDPDATA], a
  xor a
  nop
  nop
  nop
  out [VDPDATA], a
  ret
