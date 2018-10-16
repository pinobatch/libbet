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
hLocals equ $FF80
locals_size equ 16

; Bits 7-4 of floor_map entries are the same as PADF_ and PADB_
; from hardware.inc. Bits 2 and 3 are defined thus
FLOORB_DEADEND equ 2
FLOORB_ENTERED equ 3
FLOORF_DEADEND equ %00000100
FLOORF_ENTERED equ %00001000

MOVEB_JUMP      equ 2
MOVEF_JUMP      equ %00000100
MOVEF_DIRECTION equ %00000011

; 1: show dead ends when map starts
; 0: hide dead ends until entered (release)
SHOW_UNENTERED_DEADENDS equ 0

; 1: Select button restarts this level; 0: disable (release)
SELECT_RESTARTS equ 0

; 1: require score>area, half reachable, and 2 back row reachable
;    (release)
; 0: require only score>area
USE_PINO_CONSTRAINTS equ 1

; 1: use time-based seed (release); 0: use fixed seed
RANDOMIZE_SEED equ 1

; $0604: 4w x 6h, 0: size by level (release
FORCE_FLOOR_SIZE equ 0

  ENDC

