;
; SMS and Genesis controller reading for SMS
;
; Copyright 2020 Damian Yerrick
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

.ramsection "PadsWRAM" bank 0 slot WRAM0
cur_keys ds 2
new_keys ds 2
is_3button ds 2
.ends

.bank 0
.section "pads" free

.ifdef GAMEGEAR

;;
; Reads the Game Gear's controller, mapping the Start button to
; where it appears on a Genesis
read_pads:
  ; Read the D-pad and buttons 1 and 2
  in a, (JOYLO)
  cpl
  and $3F
  ld l, a

  ; Mix in the Start button
  in a, (0)
  cpl
  and $80
  or l
  ld l, a

  ; Calculate which keys have been pressed since last frame
  ld a, [cur_keys+0]
  cpl
  and l

  ; Write everything back
  ld h, 0
  ld [cur_keys], hl
  ld l, h
  ld [is_3button], hl
  ld l, a
  ld [new_keys], hl
  ret

.else

;;
; Reads controllers 1 and 2 on Master System or Genesis
; including Genesis 3-button controllers
read_pads:

  ; Load joystick page 0
  ld a, JOY_ATRIN|JOY_BTRIN|JOY_ATHHIGH|JOY_BTHHIGH
  out (JOYGPIO), A
  xor a
  ld [is_3button+0], a  ; clear 3-button flag while waiting for
  ld [is_3button+1], a  ; multiplexer in joystick to respond

  ; Read the first 6 buttons (up, down, left, right, 1/B, 2/C)
  in a, (JOYLO)
  cpl
  ld l, a     ; HL=???? ???? DUCB RLDU
  in a, (JOYHI)
  cpl
  and $0F
  ld h, a     ; HL=0000 CBRL DUCB RLDU
  ld a, JOY_ATRIN|JOY_BTRIN|JOY_ATHLOW|JOY_BTHLOW  ; Preload page 1
  out (JOYGPIO), A
  add hl, hl
  add hl, hl  ; HL=00CB RLDU CBRL DU00
  srl l
  srl l       ; HL=00CB RLDU 00CB RLDU
  
  ; Read Genesis extra buttons (A and Start) if they exist
  ; Right+Left both pressed means bits 5-4 are Start/A instead of C/B
  ; Handle player 1
  in a, (JOYLO)  ; A=~DUSA33DU
  ld c, a
  and $0C
  jr nz, @port1_not_3button
    cpl
    ld [is_3button+0], a
    xor c        ; A= DUSA33DU
    add a        ; A= USA33DU0
    add a        ; A= SA33DU00
    and $C0      ; A= SA000000
    or l         ; A= SACBRLDU
    ld l, a
  @port1_not_3button:

  ; Handle player 2
  in a, (JOYHI)  ; A=~XXXXSA33
  ld c, a
  and $03
  jr nz, @port2_not_3button
    cpl
    ld [is_3button+1], a
    xor c        ; A= XXXXSA33
    add a        ; A= XXXSA330
    add a        ; A= XXSA3300
    add a        ; A= XSA33000
    add a        ; A= SA330000
    and $C0      ; A= SA000000
    or h         ; A= SACBRLDU
    ld h, a
  @port2_not_3button:

  ; Treat Pause as the Genesis/Game Gear Start button
  ld a, [pause_pressed]
  or a
  jr z, @pause_not_pressed
    dec a
    ld [pause_pressed], a
    set 7, l
  @pause_not_pressed:

  ld a, JOY_ATRIN|JOY_BTRIN|JOY_ATHHIGH|JOY_BTHHIGH  ; Back to page 0
  out (JOYGPIO), A

  ; Calculate which keys have been pressed since last frame
  ld a, [cur_keys+0]
  cpl
  and l
  ld [new_keys+0], a

  ld a, [cur_keys+1]
  cpl
  and h
  ld [new_keys+1], a
  ld [cur_keys], hl

  ret
.endif
.ends
