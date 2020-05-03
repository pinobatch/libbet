Libbet and the Magic Floor
==========================
This is a port of Martin Korth's game _[Magic Floor]_ to the Game Boy
compact video game system, introducing Libbet the boulder girl.

One day, Libbet was rearranging her basement when she discovered
a passage to an empty hall whose floor had a peculiar pattern.
She rolled in to investigate.

The floor tiles have four shades. Libbet can roll or jump between
tiles of the same shade. She can also roll or jump onto the next
brighter shade or from white to black, which leaves a track.
Tiles with no exits contain a trap door that leads to the entrance.
Leave 90 percent of possible tracks and roll to the exit to win.

Controls:

- Control Pad: Roll
- A + Control Pad: Jump

Installation
------------
The game is written in assembly language.  Building it from source
requires [RGBDS], GNU Make, Python 3, and [Pillow] (Python Imaging
Library).  Open a terminal or command prompt, put RGBDS, Make, and
Python on your PATH, then type

    make

Once you've built it (or downloaded a binary release), it will play
in SameBoy, bgb, or mGBA emulator, or on a Game Boy through a
Catskull or EverDrive flash cart.

Achievements
------------
Performing feats in the game will earn you achievements.  Some are
harder to earn than others.

- Completionist: Complete all floors with 100% score
- Sink it: Complete a floor with 100% score, leaving the last track
  while entering a dead end
- Dash for the door: Complete a floor with 100% score, and then
  reach the exit without retreating or resting
- No peeking: Complete a floor without resting more than a second
  or inputting an invalid move
- Restless: Complete a floor while rolling continuously, without
  resting a single frame or inputting an invalid move
- No scope: Rotate the Control Pad by 360 degrees during a jump

Legal
-----
Copyright 2002, 2012 Martin Korth  
Copyright 2018, 2020 Damian Yerrick

This program is free software.  Permission is granted to use it
subject to the terms of the zlib License.  See the file `LICENSE`.


[Magic Floor]: https://problemkaputt.de/magicflr.htm
[RGBDS]: https://github.com/rednex/rgbds
[Pillow]: https://pillow.readthedocs.io/
