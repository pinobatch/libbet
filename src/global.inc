  IF  !DEF(GB_INC)
GB_INC SET 1

; things left out of hardware.inc ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

CHRRAM0 EQU $8000  ; Sprite tiles 0-127; BG tiles 0-127 if BG_CHR01 on
CHRRAM1 EQU $8800  ; Sprite and BG tiles 128-255
CHRRAM2 EQU $9000  ; BG tiles 0-127 if BG_CHR01 off

P1F_NONE     EQU $30
P1F_BUTTONS  EQU $10
P1F_DPAD     EQU $20

SGB_NONE EQU $00
SGB_SUPPORT EQU $03
REGION_J EQU $00
REGION_UE EQU $01

;;
; Syntax: drgb $FF9966 for color #FF9966
; Divides each hex tuplet by 8 and rounds down. 
drgb: macro
  dw (\1 & $F80000) >> 19 | (\1 & $00F800) >> 6 | (\1 & $0000F8) << 7
  endm

; global constants and the like ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

; Allowing different subroutines to share local variables in HRAM
; without having to declare all memory in one file requires an
; allocation strategy using ".rsset".
hLocals = $FF80
locals_size = 16


  ENDC

