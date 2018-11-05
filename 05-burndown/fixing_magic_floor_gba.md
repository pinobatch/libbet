If called from the "cartridge" entry point, Magic Floor for Game Boy
Advance tries to copy itself from 0x08000000 (ROM) to 0x02000000
(EWRAM).  This causes problems if it boots into EWRAM, as in the case
of the GBA Movie Player.  To fix this, I patched it to calculate the
source address by subtracting a value from current PC instead of
loading a constant.  That way, the source is 0x08000000 or 0x02000000
depending on how it was loaded.

The source address is loaded at start+0xC8: `mov r0,#0x08000000`

I replaced the instruction with `sub r0, pc, #0xD0` which I
hand-assembled to `0xE24F00D0`

To apply it, open MAGICFLR.GBA in a hex editor and replace the bytes
at 0x00C8 with `D0 00 4F E2`
