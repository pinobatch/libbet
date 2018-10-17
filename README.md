Libbet and the Magic Floor
=======================
This is a port of Martin Korth's game _[Magic Floor]_ to the Game Boy
compact video game system, introducing Libbet the boulder girl.

"One day, Libbet was rearranging her basement when she discovered
a passage to an empty hall whose floor had a peculiar pattern.
She rolled in to investigate."

The floor tiles have four shades. Libbet can roll or jump between
tiles of the same shade. She can also roll or jump onto the next
brighter shade or from white to black, which leaves a track.
Tiles with no exits contain a trap door that leads to the entrance.
Leave 90 percent of possible tracks and roll to the exit to win.

Controls:

- Control Pad: Roll
- A + Control Pad: Jump

The game is written in assembly language.  Building it from source
requires [RGBDS], GNU Make, Python 3, and [Pillow] (Python Imaging
Library).

Free software license pending.


[Magic Floor]: https://problemkaputt.de/magicflr.htm
[RGBDS]: https://github.com/rednex/rgbds
[Pillow]: https://pillow.readthedocs.io/
