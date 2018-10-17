In a private message on forums.nesdev.com,
`tepples` (Damian Yerrick) wrote on 2018-10-02:

> Would you be interested in someone porting the game to the original
> Game Boy?

`nocash` (Martin Korth) replied on 2018-10-03:

> Would be fine.  Although I might like to do that myself someday
> for gameboy, too.  But it wouldn't be any problem to me, even if
> it should end up with two different gameboy versions.  Or maybe
> I could host the ported source code made by somebody else.
> [...]
> Would be also interesting to see if somebody does (or doesn't)
> come up with completely different tile designs or the like.

Once I secured permission, I got to work.

1. Play the NES version for a while to understand how to play and
   where any pain points are.  Come up with tile designs that are
   distinctive enough in both shade and texture for the low-contrast
   monochrome passive-matrix STN LCD of the original Game Boy.
2. The game's intro mentions "you are a boulder".  Design and animate
   a "boulder girl" inspired by the pear-shaped Terra-Firmians from
   _DuckTales_ episode "Earth Quack".  Write a Python tool to read
   sprites off a sprite sheet.
3. Write a reference implementation of floor generation in Python.
   Add constraints to reject unplayable floors.  To the original,
   which only ensured maximum score >= area, I added three: same
   number of cells of all colors, two round trip reachable cells
   in the back row, and at least half of area round trip reachable.
4. Attempt to model the boulder girl in Blender to see if that helps
   with certain perspective problems I encountered in phase 2.
   Discover that a shadow is essential to communicate jumping north
   or south to the player, particularly in the confused perspective
   common among 8-bit overhead games, where the background is
   semi-overhead but the moving characters are drawn as if viewed
   from the side.  Upload the repository to GitHub, carefully
   stepping around the title, as I felt disclosing its title too
   early would lead to unrealistic expectations of the project's
   completion schedule among those who follow my work.
5. Coding begins.  Compress the tile designs, generate and render a
   floor, move a plain boulder on the floor, track score, open a door
   at the far end once score reaches 90 percent of maximum, replace
   the plain boulder with the animated boulder girl, and sequence the
   floor sizes.  This leaves us two weeks later with a 6502-byte
   Game Boy game.
