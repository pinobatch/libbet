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
The game plays in SameBoy, Emulicious, bgb, or mGBA emulator, or on a
Game Boy through an EverDrive GB or EZ-Flash Junior flash cart.
Visual problems may appear in VisualBoyAdvance and other outdated
emulators.

The game is not yet ported to Mega Duck or Analogue Pocket, as
supply chain problems have prevented the developer from procuring
a system on which to test it.

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

Building
--------

Building the game requires [RGBDS] 0.7 or later, [Python] 3,
[Pillow], [GNU Make], and GNU Coreutils.  Once you have these
installed, run this command:

    make

If you're using Windows and not using WSL, it may be convenient to
obtain Coreutils through [Git for Windows], which contains a
distribution of MSYS2.  To add GNU Make to Git for Windows, follow
[evanwill's instructions] to download the latest Make without Guile
from [ezwinports].

[RGBDS]: https://rgbds.gbdev.io/install
[Python]: https://www.python.org/
[Pillow]: https://pillow.readthedocs.io/
[GNU Make]: https://www.gnu.org/software/make/
[Git for Windows]: https://git-scm.com/download/win
[evanwill's instructions]: https://gist.github.com/evanwill/0207876c3243bbb6863e65ec5dc3f058
[ezwinports]: https://sourceforge.net/projects/ezwinports/files/

Legal
-----
Copyright 2002, 2012 Martin Korth  
Copyright 2018, 2024 Damian Yerrick

This program is free software.  Permission is granted to use it
subject to the terms of the zlib License.  See the file `LICENSE`.


[Magic Floor]: https://problemkaputt.de/magicflr.htm
[RGBDS]: https://rgbds.gbdev.io/install
[Python]: https://www.python.org/
[Pillow]: https://pillow.readthedocs.io/
[GNU Make]: https://www.gnu.org/software/make/
