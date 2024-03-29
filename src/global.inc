;
; hardware.inc supplement for Game Boy programs
;
; Copyright 2018, 2019 Damian Yerrick
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

  IF  !DEF(GB_INC)
def GB_INC equ 1

; call graph annotation ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

macro fallthrough
  assert (\1) == @
endm

macro calls
endm

macro tailcalls
endm

macro jumptable
endm

macro local
endm

; things left out of hardware.inc ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

def CHRRAM0 EQU $8000  ; Sprite tiles 0-127; BG tiles 0-127 if BG_CHR01 on
def CHRRAM1 EQU $8800  ; Sprite and BG tiles 128-255
def CHRRAM2 EQU $9000  ; BG tiles 0-127 if BG_CHR01 off

;;
; Syntax: drgb $FF9966 for color #FF9966
; Divides each hex tuplet by 8 and rounds down. 
macro drgb
  dw (\1 & $F80000) >> 19 | (\1 & $00F800) >> 6 | (\1 & $0000F8) << 7
endm

;;
; Syntax: ldxy rp, xpos, ypos, mapbase
; Sets a register pair to the address of (x, y) tile coordinates
; within a tilemap.
; @param rp a register pair (BC, DE, HL)
; @param x horizontal distance in tiles from left (0-31)
; @param y vertical distance in tiles from top (0-31)
; @param mapbase start address of 32-cell-wide tilemap:
;   SCRN_BG (default), _SCRN0, _SCRN1, or a virtual tilemap in WRAM.
macro ldxy
  if _NARG < 4
    ld \1, (\3) * SCRN_VX_B + (\2) + SCRN_BG
  else
    ld \1, (\3) * SCRN_VX_B + (\2) + (\4)
  endc
endm

; global constants and the like ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

; Bits 7-4 of floor_map entries are the same as PADF_ and PADB_
; from hardware.inc. Bits 2 and 3 are defined thus
def FLOORB_DEADEND equ 2
def FLOORB_ENTERED equ 3
def FLOORF_DEADEND equ %00000100
def FLOORF_ENTERED equ %00001000

def MOVEB_JUMP      equ 2
def MOVEF_JUMP      equ %00000100
def MOVEF_DIRECTION equ %00000011

; It is not strictly necessary to completely clear the display list,
; as lcd_clear_oam writes a "hide this sprite" value to all unused
; sprites.  But when Options > Exceptions > Unitialized RAM >
; break on read (reset) is on, BGB complains about copying
; uninitialized data to OAM even if said data is provably unused.
; So put "shut BGB up" commands behind a conditional.
def bgbcompat equ 1

; In `di halt` scenarios, VisualBoyAdvance 1.7.2 can call the
; interrupt handler anyway.  When this is turned on, include a
; do-nothing STAT handler.
def vbacompat equ 1

; 1: show dead ends when map starts
; 0: hide dead ends until entered (release)
def SHOW_UNENTERED_DEADENDS equ 0

; 1: Select button restarts this level; 0: disable (release)
def SELECT_RESTARTS equ 0

; 1: require score>area, half reachable, and 2 back row reachable
;    (release)
; 0: require only score>area
def USE_PINO_CONSTRAINTS equ 1

; 1: use time-based seed (release); 0: use fixed seed
def RANDOMIZE_SEED equ 1

; $0604: 4w x 6h, 0: size by level (release
def FORCE_FLOOR_SIZE equ 0

; There's a bug in BGB's implementation of 127-step noise.
; GB stops a noise early under certain conditions; BGB does not.
def TEST_PNOISE_BUG equ 0

; Do we build code for autorepeat and Super Game Boy detection?
def USE_DAS equ 0
def DETECT_SGB equ 1

; Do we save what Game Boy type is running, or do we just use it
; to skip the logo fade?
def SAVE_GB_TYPE equ 1

; Do we display a variable in-game?
def USE_DEBUGHEX equ 0

; Both instructions and debrief use vwf_page_init, which defines a
; plane subject to this shape
def vwf_page_width equ 16
def vwf_page_first_tileid equ 256 - 8 * vwf_page_width

; achievements needs NUM_FLOORS to calculate Completionist
; this is 5 for production or often 2 for debugging
def NUM_FLOORS equ 6
def FIRST_ACH_FLOOR equ 1  ; no achievements from tutorial

; 1: use the attract mode floor for a predictable
; when testing achievements
def USE_ATTRACT_FLOOR equ 0

; 1: Hold Start to pause
def SPRING_LOAD_PAUSE equ 0

; 2019-02-21: mattcurrie in gbdev Discord wanted a game to test with
; that uses $9C00 for playfield and $9800 for window
def SWAP_SCRNS equ 0

  if DEF(_SCRN1)
  if SWAP_SCRNS
def SCRN_BG equ _SCRN1
def SCRN_WIN equ _SCRN0
def LCDCF_SCRNADDR equ LCDCF_WIN9800|LCDCF_BG9C00
  else
def SCRN_BG equ _SCRN0
def SCRN_WIN equ _SCRN1
def LCDCF_SCRNADDR equ LCDCF_WIN9C00|LCDCF_BG9800
  endc
  endc

; Achievement-related constants ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

def ACH_100PCT         equ 0
def ACH_100PCT_DEADEND equ 1
def ACH_DASH_FOR_DOOR  equ 2
def ACH_NO_PEEKING     equ 3
def ACH_RESTLESS       equ 4
def ACH_AIRROT         equ 5  ; rotate Control Pad 360 deg during a distance 2 move
def NUM_ACHIEVEMENTS   equ 6

; move_flags constants related to the achievements
; Sink it, Restless, and Dash for the door
; Moving without MOVED_ONCE clears PEEKED_SINCE_START
; Moving sets MOVED_ONCE and MOVED_SINCE_100
; Not moving in a frame sets PAUSED_SINCE_*
; Advancing from a FRLF_KEEPROLL frame sets PEEKED_SINCE_START
; Moving farther from the exit sets RETREATED_SINCE_100
; 100% clears PAUSED_SINCE_100, RETREATED_SINCE_100,
;   and MOVED_SINCE_100
; Exit without PAUSED_SINCE_100 or RETREATED_SINCE_100 earns
;   Dash for the door
; Exit without MOVED_SINCE_100 (possible only by landing on a
;   dead end) earns Sink it
; Exit without MVFB_PEEKED_SINCE_START earns No peeking
def MVFB_MOVED_ONCE          equ 7
def MVFB_RETREATED_SINCE_100 equ 6
def MVFB_MOVED_SINCE_100     equ 5
def MVFB_PAUSED_SINCE_100    equ 4
def MVFB_PEEKED_SINCE_START  equ 1
def MVFB_PAUSED_SINCE_START  equ 0

; If this many tracks are laid without hesitation, award Restless.
; Usually this'll be about 15 or so.  If it's 0, Restless is
; instead awarded at exit if MVFB_PAUSED_SINCE_START is clear,
; like a hardcore version of No peeking.
def RESTLESS_TRACKS equ 0

  ENDC
