.include "src/sms.inc"

.asciitable
map " " to "~" = $20
.enda

.def STACK_SIZE 60
.export STACK_SIZE

.ramsection "StackAndSAT" bank 0 slot WRAM0 align 256
stack_top ds STACK_SIZE
sat_unused1 db
sat_unused2 db
sat_unused3 db
sat_used db  ; SAT fill level: $40 minimum, $80 maximum
sat_y ds NUM_SPRITES
sat_xn ds NUM_SPRITES*2
.ends

.ramsection "MainWRAM" bank 0 slot WRAM0
; This variable actually counts IRQs, not NMIs.  But it's called
; "nmis" for consistency with my project templates on two other
; consoles that use NMI for vertical blank.
nmis db
pause_pressed db
debughex0 db
debughex1 db
cur_score db
max_score db
cur_combo db
.ends

.bank 0 slot 0


; Fixed entry points: reset, RST $38 (IRQ), and NMI (pause)

; IRQ handler in SMS has a fixed address $0038, shared by the vblank,
; hblank, and vcount interrupts (like STAT on Game Boy).  This means
; a handler may have to distinguish them otherwise.  It also means
; that unfortunately, we can't use RST $38 for an error handler for
; execution falling into padding the way ISSOtm's Game Boy code does.
.org $0038
.section "irqhandler" force
  push af
  in a, (VDPSTATUS)
  ld a, (nmis)
  inc a
  ld (nmis), a
  pop af
  ei
  reti

.ends

.org $0066
.section "pausehandler" force
  ; Set a flag to cause the controller handler to read Start on
  ; controller 1 briefly
  push af
  ld a, 5
  ld [pause_pressed], a
  pop af
  retn
.ends


; Main program ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
.section "main" free
main:

.if 1==0
  ; Sprites use the second half of CRAM, at C010-C01F on SMS
  ; or C000-C01F on GG.
  vdp_seek $C010
  ld hl,ObjPaletteData
  ld bc,(ObjPaletteDataEnd-ObjPaletteData)*256+VDPDATA
  otir
.endif

  di
  call vdp_clear_sat
  call draw_bg
  ei

  ; Turn screen on
  ld a,MODEF_ON|MODEF_VIRQ
  out (VDPCTRL),a
  ld a,VDPMODE
  out (VDPCTRL),a
  xor a
  ld (nmis), a

  ; Game logic
  forever:
    ; Read controller 1 and move the sprite
    call read_pads

    ; Draw sprites
    ld hl, sat_used
    ld [hl], $40

    call wait_vblank_irq
    call vdp_push_sat

    ld a, [new_keys]
    ;bit 7, a
    ;jr nz, main
    bit 4, a
    jr z, forever
    jr forever

draw_bg:

  ; disable display while loading
  in a, (VDPSTATUS)
  xor a
  out (VDPCTRL),a
  ld a,VDPMODE
  out (VDPCTRL),a

  ; Load background palette data into the first half of CRAM,
  ; at VDP addresses C000-C00F on SMS or C000-C01F on GG.
  vdp_seek $C000
  ld hl,PaletteData
  ld bc,(PaletteDataEnd-PaletteData)*256+VDPDATA
  otir

  ; Clear the pattern table
  vdp_seek_tile 0
  ld a, $55
  ld d, 40/8
  call vmemset_256d

  ; Clear nametable and SAT
  call vdp_clear_nt

  ; load vwfcanvas
  vdp_seek_xy 8, 11
  ld c, 16
  ld b, c
  @loop:
    ld a, c
    inc c
    out [VDPDATA], a
    xor a
    out [VDPDATA], a
    djnz @loop

  call vwfClearBuf
  ld hl, hello_msg
  ld b, 4
  call vwfPuts  

  vdp_seek_tile 16
  ld hl, lineImgBuf
  ld d, 1
  call load_1bpp_font
  
  call load_status_chr
  call init_status_bar
;  call draw_debughex

  ret

PaletteData:
  drgb $000000,$555555,$AAAAAA,$FFFFFF
PaletteDataEnd:
hello_msg:
  .db "Nothing to see; move along", 0
.ends