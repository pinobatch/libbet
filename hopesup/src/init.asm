;
; Move Podge (SMS): ROM header and CPU/VDP init
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

; ROM header ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

; SMS and GG ROMs are supposed to have a header at $7FF0
; to let the BIOS know the cartridge connector is clean.
; https://www.smspower.org/Development/ROMHeader
; 7FF0: "TMR SEGA"
; 7FFA: Sum of all bytes in ROM outside $7FF0-$7FFF, mod 65536
; 7FFC: BCD product code digits tens and ones
; 7FFD: BCD product code digits thousands and hundreds
; 7FFE: D7-4 BCD product code divided by 10000; D3-0 release version
; 7FFF: D7-4 4 for Master System or 6 for Game Gear;
;       D3-0 ROM size covered by checksum (C: 32 KiB; E: 64 KiB;
;       F: 128 KiB; 0: 256 KiB; 1: 512 KiB).  This is often smaller
;       than ROM; WLA always uses C (32 KiB).
; 
; The header in Genesis, Game Boy, Super NES, and GBA ROMs contains
; additional info, such as title and publisher.  SMS/GG does not.
; So the homebrew community built SDSC to populate the title bar.
; https://www.smspower.org/Development/SDSCHeader
; 7FE0: "SDSC"
; 7FE4: BCD major version
; 7FE5: BCD minor version
; 7FEA: Pointer to author
; 7FEC: Pointer to title
; 7FEE: Pointer to description
; All strings use ASCII encoding ($20-$7E) with trailing $00.
; Description may also include line breaks: $0D, $0D $0A, or $0A.
; Pointer values $FFFF and $0000 are treated as "data missing".
; WLA DX offers a shortcut command to specify all these in the order
; 7FE4, 7FEC, 7FEE, 7FEA.  It also fills the BIOS header as above.
.sdsctag 0.01,"Sample text","Don't get your hopes up.","Damian Yerrick"

; A header is needed to mark a ROM as being for Game Gear or not.
; TODO: File issue about these:
; WARNING: .COMPUTESMSCHECKSUM is unnecessary when .SMSHEADER is defined.
; WARNING: .SMSTAG is unnecessary when .SMSHEADER is defined.
.SMSHEADER
  PRODUCTCODE 99, 99, 9 ; 2.5 bytes
  VERSION 2             ; 0-15
  .ifdef GAMEGEAR
    REGIONCODE 6
  .else
    REGIONCODE 4
  .endif
.ENDSMS

; Initialization ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

.bank 0
.org $0000
.section "rst00" force
  ; Configure interrupt mode and stack
  ; First 8 bytes so we can leave RST $08-$30 free for other purposes
  di
  im 1
  ld sp, stack_top + STACK_SIZE
  jr init_part2
.ends

; Place this part of init between the IRQ handler and the pause handler
.org $0048
.section "init_part2" force
; Between the IRQ handler and the pause button handler are another
; 32 bytes for init
init_part2:
  ; Put the VDP into mode 4, with NT at $7800 and SAT at $7F00.
  ; There's no dance of waiting 2 frames for the VDP to wake up.
  ld hl,vdp_regvalues
  ld bc,(vdp_regvalues_end-vdp_regvalues)*256+VDPCTRL  ; B: count; C: output port
  otir

  ; Set all audio channels to center
  ld a, $FF
  .ifdef GAMEGEAR
    out (DCSG_PAN), a
  .endif

  ; Set all volumes to 0
  ld b, $10

  out (DCSG), a
  sub b
  out (DCSG), a
  sub b
  out (DCSG), a
  sub b
  out (DCSG), a
  
  ; TODO: do something to joystick DDR possibly?

  jp main
.ends

.section "init_part2_regvalues" free
; Data to initialize VDP to mode 4
vdp_regvalues:
  .db MASKF_SMS,VDPMASK
  .db $00,VDPMODE
  .db $ff,VDPNTADDR
  .db $ff,VDP83
  .db $ff,VDP84
  .db $ff,VDPSATADDR
  .db $07,VDPOBSEL
  .db $10,VDPBORDER
  .db $00,VDPSCX
  .db $00,VDPSCY
  .db $ff,VDPPIT
vdp_regvalues_end:
.ends
