How to port _Magic Floor_
=========================

Martin Korth developed a search game titled _[Magic Floor]_ as
a sample ROM to use with his nocash line of console emulators.
After the initial version for Game Boy Advance, he ported it
to numerous other platforms covered by his emulators:

- Nintendo DS, Nintendo DSi, and e-Reader
- ZX81 and Jupiter ACE
- Atari 2600
- Famicom, NES, and PlayChoice 10
- Super Famicom, Super NES, Nintendo Super System, Satellaview BSX,
  and Sony Super Disc (the "Nintendo PlayStation" prototype)
- The on-screen display of AMT630A, a display panel intended for
  cars' rear-view cameras

However, it remained unported to Game Boy, the platform emulated
by the oldest of these emulators (NO$GMB), until 2018 when
Damian Yerrick produced a port titled _Libbet and the Magic Floor_.

However, other platforms emulated by nocash emulators lack a port:

- Commodore 64
- MSX
- Amstrad CPC
- PlayStation

As do several video game consoles of comparable vintage:

- ColecoVision and Sega SG-1000
- Atari 400, 800, and 5200
- Atari 7800
- Atari Lynx
- Sega Mark III, Master System, and Game Gear
- PC Engine and TurboGrafx-16
- Mega Drive, Genesis, Sega CD, and Nomad
- Neo Geo
- Atari Jaguar
- Sega Saturn

Development of _Libbet_ followed roughly the following steps.  A port
to another platform could follow a similar track.  This describes
only the order in which program features were added, excluding bug
fixes, optimizations, refactoring, and changes to assets.

[Magic Floor]: https://problemkaputt.de/magicflr.htm

v0.01
-----
This produced a game equivalent to the original plus rolling animation.

1. Draw the background graphics
2. Draw the character's sprite sheet and prototype the animation
3. Prototype the floor generation in Python
4. Load the textures into video memory
5. Load the textures to draw cells in the floor
6. Draw a predefined floor
7. Port floor generation to assembly language
8. Draw the border around the floor
9. Generate and draw floors of different sizes
10. Draw a status bar
11. Move a sprite that skips around by the distance of one cell
12. Make only valid movements
13. Calculate and draw score
14. Import a font routine
15. Add a static title screen with instructions
16. Add exit door that opens once score is high enough
17. Animate the character rolling and jumping between cells
18. Notify Martin
19. Generate five floor sizes in sequence

v0.02
-----

1. Draw an exit indicator for floors too tall for a door
2. Fade-in and fade-out
3. Attract mode using the predefined floor
4. Animate falling into a dead end and launching out
5. Add sound effects

v0.03 was mostly size optimizations and fine-tuning of cels and audio.

v0.04
-----

1. Document how to record video from an emulator and encode it
2. Add a hex digit display that can be used for various purposes
3. Gamepad button combination to reset
4. Award "Completionist" achievement
5. Display floor scores and achievements at end
6. Award "Dash for the door", "Sink it", "No peeking", "Restless",
   and "No scope"
7. Display achievement in status bar
8. Display combo in status bar

v0.05
-----

1. Fade more smoothly with temporal dithering
2. Open with character rolling across the screen, leaving behind
   copyright notice
3. Display animation for a combo ending
4. Add buzz for invalid move
