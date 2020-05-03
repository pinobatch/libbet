;
; Sega Master System I/O definitions
;
; Copyright 2019, 2020 Damian Yerrick
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


; SMS port definitions ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;
; These ports are directly visible to the Z80

; 7654 3210
; |||| |+--- 1: Disable joystick I/O
; |||| +---- 1: Disable BIOS ROM
; |||+------ 1: Disable work RAM at $C000-$FFFF
; ||+------- 1: Disable Sega Card slot
; |+-------- 1: Disable cartridge slot
; +--------- 1: Disable expansion slot
.def MEMCTRL $3E

; 7654 3210
; |||+-|||+- Port A TR pin (00: output low; 10: output high; 11: input)
; ||+--||+-- Port A TH pin (00: output low; 10: output high; 11: input)
; |+---|+--- Port B TR pin (00: output low; 10: output high; 11: input)
; +----+---- Port B TH pin (00: output low; 10: output high; 11: input)
; TR is the 2/C button.
; The Light Phaser uses TH as an input to latch the HV counter.
; The 3-button controller for Mega Drive and Genesis uses TH as an
; output to select Start/A vs. C/B.  To detect this controller, set
; TH low and look for Left+Right being pressed (0) at once.
; The 6-button controller returns Up+Down+Left+Right on the third
; TH low in a frame, after which the following TH high returns
; C, B, Mode, X, Y, Z.
.def JOYGPIO $3F
.def JOY_ATRLOW  $00
.def JOY_ATRHIGH $10
.def JOY_ATRIN   $11
.def JOY_ATHLOW  JOY_ATRLOW  << 1
.def JOY_ATHHIGH JOY_ATRHIGH << 1
.def JOY_ATHIN   JOY_ATRIN   << 1
.def JOY_BTRLOW  JOY_ATRLOW  << 2
.def JOY_BTRHIGH JOY_ATRHIGH << 2
.def JOY_BTRIN   JOY_ATRIN   << 2
.def JOY_BTHLOW  JOY_ATRLOW  << 3
.def JOY_BTHHIGH JOY_ATRHIGH << 3
.def JOY_BTHIN   JOY_ATRIN   << 3

.def VDPLY $7E
.def VDPLX $7F
.def VDPDATA $BE
.def VDPCTRL $BF
.def VDPSTATUS $BF

; FEDC BA9876 543210
; || | |||||| |||||+- 0: Port A Up pressed
; || | |||||| ||||+-- 0: Port A Down pressed
; || | |||||| |||+--- 0: Port A Left pressed
; || | |||||| ||+---- 0: Port A Right pressed
; || | |||||| |+----- 0: Port A button 1/B pressed
; || | |||||| +------ 0: Port A button 2/C pressed (TR)
; || | |||||+-------- 0: Port B Up pressed
; || | ||||+--------- 0: Port B Down pressed
; || | |||+---------- 0: Port B Left pressed
; || | ||+----------- 0: Port B Right pressed
; || | |+------------ 0: Port B button 1/B pressed
; || | +------------- 0: Port B button 2/C pressed (TR)
; || +--------------- 0: Reset pressed
; |+----------------- Port A TH input
; +------------------ Port B TH input
; On Japanese consoles, TH and TR inputs always return 0 when set to
; output.  On export consoles, TH and TR inputs reflect output level.
.def JOYLO $DC
.def JOYHI $DD
.def PADB_2       5
.def PADB_1       4
.def PADB_RIGHT   3
.def PADB_LEFT    2
.def PADB_DOWN    1
.def PADB_UP      0
.def PADF_1       1<<PADB_1
.def PADF_2       1<<PADB_2
.def PADF_RIGHT   1<<PADB_RIGHT
.def PADF_LEFT    1<<PADB_LEFT
.def PADF_DOWN    1<<PADB_DOWN
.def PADF_UP      1<<PADB_UP
.def JOYHIB_TH_B  7
.def JOYHIB_TH_A  6
.def JOYHIB_RESET 4
.def JOYHIF_TH_B  1<<JOYHIB_TH_B
.def JOYHIF_TH_A  1<<JOYHIB_TH_A
.def JOYHIF_RESET 1<<JOYHIB_RESET

; SMS VDP register definitions ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;
; The VDP has a 16-bit address space.
; 0000-3FFF: Read VRAM (autoinc 1)
; 4000-7FFF: Write VRAM (autoinc 1)
; 8000-8AFF: Set register H to value L
; C000-C01F: Write CRAM (autoinc 1)
;
; To write to a VDP register, write the value to VDPCTRL
; then the register number ($80-$8A) to VDPCTRL.

.macro vdp_seek
  ld a, <(\1)
  out (VDPCTRL), a
  ld a, >(\1)
  out (VDPCTRL), a
.endm

.macro vdp_seek_xy
  vdp_seek $7800 + (\1) * 2 + (\2) * 64
.endm

.macro vdp_seek_tile
  vdp_seek $4000 + (\1) * 32
.endm

.macro ldxy_hl
  ld hl, $7800 + (\1) * 2 + (\2) * 64
.endm

.macro ldxy_de
  ld de, $7800 + (\1) * 2 + (\2) * 64
.endm

.def VDPMASK $80
.def MASKB_RFIX   7  ; disable vertical scrolling for columns 24-31
.def MASKB_TFIX   6  ; disable horizontal scrolling for rows 0-1
.def MASKB_LCLIP  5  ; draw left 8 pixels with border color (like NES)
.def MASKB_HIRQ   4  ; call interrupt $38 at start of hblank
.def MASKB_OBJL8  3  ; move all sprites left by 8 pixels (like GB)
.def MASKB_SMS    2  ; use Master System video mode (not TMS9918 emulation)
.def MASKB_GRAY   0  ; emit no color burst (mehikon mode)
.def MASKF_RFIX   1<<MASKB_RFIX
.def MASKF_TFIX   1<<MASKB_TFIX
.def MASKF_LCLIP  1<<MASKB_LCLIP
.def MASKF_HIRQ   1<<MASKB_HIRQ
.def MASKF_OBJL8  1<<MASKB_OBJL8
.def MASKF_SMS    1<<MASKB_SMS
.def MASKF_GRAY   1<<MASKB_GRAY

.def VDPMODE $81
.def MODEB_ON     6  ; 1: display; 0: blanking
.def MODEB_VIRQ   5  ; call interrupt $38 at start of vblank
.def MODEB_8X16   1  ; sprites are 16 pixels tall
.def MODEB_MAG    0  ; pixel double front 4 sprites (SMS1) or all
                     ; sprites (SMS2); ignored on Genesis PBC
.def MODEF_ON     1<<MODEB_ON
.def MODEF_VIRQ   1<<MODEB_VIRQ
.def MODEF_8X16   1<<MODEB_8X16
.def MODEF_MAG    1<<MODEB_MAG

; 7654 3210  VDP nametable address
;      |||+- Must be 1
;      +++-- Start of nametable in 2048-byte units ($0000, $0800, ..., $3800)
;
; The nametable is 28 rows of 32 16-bit words
; FEDC BA98 7654 3210
; |||| |||+-++++-++++- Tile address in 32-byte units
; |||| ||+------------ Horizontal flip
; |||| |+------------- Vertical flip
; |||| +-------------- 0: Use CRAM $C000+; 1: Use CRAM $C010+
; |||+---------------- Display opaque pixels in front of sprites
; +++----------------- Application use
.def VDPNTADDR $82

.def VDP83 $83  ; Attribute table address. Write $FF if not on SG-1000
.def VDP84 $84  ; Background pattern table address. Write $FF if not on SG-1000

; 7654 3210  VDP sprite attribute table address
;  ||| |||+- Must be 1
;  +++-+++-- Start of sprite list in 256-byte units
;
; SAT $00-$3F are Y positions, with 0 meaning Y=1 like on NES
; SAT $80, $82, $84, ..., $FE are X positions
; SAT $81, $83, $85, ..., $FF are tile addresses in $20-byte units
; Y=$D0 terminates the SAT
.def VDPSATADDR $85
.def NUM_SPRITES 64

; 7654 3210
; |||| ||++- Must be 1
; |||| |+--- Start of sprite pattern table ($0000 or $2000)
; ++++-+---- Most sources say unused.  Troubleshooting of MDFourier
;            is ongoing.
.def VDPOBSEL $86

.def VDPBORDER $87  ; Offset into CRAM ($10-$1F) used to draw border

; Horizontal scroll position, per scanline.  Adding 1 to SCX shifts
; all pixels to the right, which is backwards from how background
; scrolling works on Nintendo consoles and more similar to sprites.
.def VDPSCX $88

; Vertical scrolling is not inverted; adding 1 shifts everything up.
; But changes are delayed to the next frame, ruling out not only the
; Demotronic trick but also Rad Racer hills.  Even status bars are
; a pain.  Scrolling wraps at 224 in the normal 192-line mode.
.def VDPSCY $89

; Scanline-counting timer that works a little like MMC3's
.def VDPPIT $8A

; The bits of VDPSTATUS are analogous to NES $2002, but in
; bit order 75600000
; NES clears vblank, over, and hit at end of vblank.  SMS clears none.
; SMS clears vblank, over, and hit on status read.  NES clears vblank.
; Like NES, reads clear the first/second write toggle.
.def STATB_VBLANK 7  ; true if vblank has begun
.def STATB_OVER   6  ; true if 9 sprites have been seen on a line
.def STATB_HIT    5  ; true if two sprites' opaque pixels have overlapped
.def STATF_VBLANK 1<<STATB_VBLANK
.def STATF_OVER   1<<STATB_OVER
.def STATF_HIT    1<<STATB_HIT

; Color palette definition
.macro drgb
  .rept NARGS
    .ifdef GAMEGEAR
      .dw ((\1 & $F00000) >> 12) | ((\1 & $F000) >> 8) | ((\1 & $F0) >> 4)
    .else
      .db ((\1 & $C00000) >> 22) | ((\1 & $C000) >> 12) | ((\1 & $C0) >> 2)
    .endif
    .shift
  .endr
.endm

; Audio command definitions ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

; Summary of opcodes for the Texas Instruments SN76489AN
; Dirt Cheap Sound Generator (DCSG)
; at SMS/GG port $7E 
;
; 00-3F: Bits 9-4 of previous square period, or all bits of others
; 40-7F: Alias of 00-3F
; 80-8F: Square 1 period low
; 90-9F: Square 1 volume in -2 dB units (0: high; 14: low; 15=off)
; A0-AF: Square 2 period low
; B0-BF: Square 2 volume
; C0-CF: Square 3 period low
; D0-DF: Square 3 volume
; E0-E7: Noise timbre and clock source
;        0: 1/16 pulse wave; 4: hiss
;        0: 7 kHz; 1: 3.5 kHz; 2: 1.7 kHz; 3: Square 3 rises
; E8-EF: Alias of E0-E7
; F0-FF: Noise volume
;
; Periods are in units of 32 cycles, such that the maximum ($3FF)
; produces (315/88*1000000/32)/1023 = 109.3 Hz

.def DCSG $7E
.def DCSG_SQ1FREQ  $80
.def DCSG_SQ1VOL   $90
.def DCSG_SQ2FREQ  $A0
.def DCSG_SQ2VOL   $B0
.def DCSG_SQ3FREQ  $C0
.def DCSG_SQ3VOL   $D0
.def DCSG_NOISECFG $E0
.def DCSG_NOISEVOL $F0

.def DCSG_NOISE_BUZZ $00
.def DCSG_NOISE_HISS $04
.def DCSG_NOISE_7K   $00
.def DCSG_NOISE_3_5K $01
.def DCSG_NOISE_1_7K $02
.def DCSG_NOISE_SQ3  $03

; Like the Game Boy, the Game Gear has stereo audio output to the
; headphone jack, panned hard left, center, or hard right through
; panning bits in port $06.
; 
; Semantics are the same as the GB's pan register NR51 ($FF25):
; - left in bits 7-4 and right in bits 3-0.
; - noise in bits 7 and 3 and tones in bits 6-4 and 2-0.
; - 0 for mute and 1 for play
;
; 7654 3210  Port $06: Audio panning
; |||| |||+- Play square 1 on right speaker
; |||| ||+-- Play square 2 on right speaker
; |||| |+--- Play square 3 on right speaker
; |||| +---- Play noise on right speaker
; |||+------ Play square 1 on left speaker
; ||+------- Play square 2 on left speaker
; |+-------- Play square 3 on left speaker
; +--------- Play noise on left speaker
;
; Or equivalently:
;
; 7654 3210  Port $06: Audio panning
; |||+-|||+- Square 1 pan (10: left; 11: center; 01: right)
; ||+--||+-- Square 2 pan (10: left; 11: center; 01: right)
; |+---|+--- Square 3 pan (10: left; 11: center; 01: right)
; +----+---- Noise pan (10: left; 11: center; 01: right)
;
; SMS programs SHOULD NOT write to this port because writes go to
; the memory control register, which enables and disables the
; cartridge slot, card slot, and work RAM.

.def DCSG_PAN $06
.def DCSG_SQ1_R   $01
.def DCSG_SQ1_C   $11
.def DCSG_SQ1_L   $10
.def DCSG_SQ2_R   $02
.def DCSG_SQ2_C   $22
.def DCSG_SQ2_L   $20
.def DCSG_SQ3_R   $04
.def DCSG_SQ3_C   $44
.def DCSG_SQ3_L   $40
.def DCSG_NOISE_R $08
.def DCSG_NOISE_C $88
.def DCSG_NOISE_L $80

; WLA DX banking setup: 32K Sega Card game ;;;;;;;;;;;;;;;;;;;;;;;;;;
;
; This banking setup is for a 32 KiB no-MBC cartridge or Sega Card.
; If there were an MBC, there would be ROMX.
; The WRAM0 slot avoids $dff0-$dfff because mapper ports overlap it.
.def ROM0 0
.def WRAM0 1
.memorymap
defaultslot ROM0
slotsize   $8000
slot ROM0  $0000
slotsize   $1FF0
slot WRAM0 $C000
.endme

.rombankmap
bankstotal 1
banksize $8000
banks 1
.endro
