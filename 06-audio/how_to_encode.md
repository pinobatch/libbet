Video encoding notes
====================

When promoting a release of a retro console game, it is often
desirable to encode gameplay as a video file.

How to set a fairly realistic palette
-------------------------------------

The default palette that bgb uses for monochrome games doesn't look
much like a Game Boy.  Its white, in particular, looks a lot more
turquoise than the yellow of the GB screen.  The following is closer
to actual appearance while remaining easy to remember in hex form:

    #CCCC44 rgb(204,204,68)
    #88AA44 rgb(136,170,68)
    #448844 rgb(68,136,68)
    #006644 rgb(0,102,68)

In Options, open GB Colors.  Select the first of the four colors to
the left of "Interpolate", then enter the numbers after `rgb` in the
fields.  Repeat for each color.  Or as a shortcut, enter only the
first and last colors and then click "Interpolate".

How to make AVIs in bgb
-----------------------

In Options, open "Sound" and enable "WAV file writer" and "record
AVI", output, then Apply.  Play the demo, then disable them and hit
Apply when the demo ends.

By default, bgb encodes uncompressed AVI files using the `DIB` codec.
If you are using 32-bit bgb, you can make smaller lossless files
using [CamStudio Lossless Codec].  Download and run its installer,
then in Sound, change the codec from `DIB` to `CSCD`.  To confirm
that the codec works, click "Config".  If this button displays an
alert box stating "Unable to open codec", the codec is not installed
or otherwise not usable.  (Note: You will *not* be able to use CSCD
or any other 32-bit software on a Mac running macOS 10.15 or later.)

[CamStudio Lossless Codec]: https://sourceforge.net/projects/camstudio/files/legacy/

How to encode
-------------

Using FFmpeg, with the appropriate codecs installed, on a computer
in the appropriate country:

    ffmpeg -y -i bgb-1567896789.avi -i bgb-1567896789.wav \
      -vf "tblend=all_mode=average, framestep=2, scale=320:288:sws_flags=neighbor" \
      -pix_fmt yuv420p -ab 64000 -movflags +faststart out.mp4

What does this mean?

* `-y`: Overwrite previous encode if any
* `-i`: Video and audio track inputs
* `-vf`: Apply a chain of video filters
    1. `tblend`: Average consecutive frames
    2. `framestep`: Cut the frame rate exactly in half, as DMG games
       don't need to run faster than 30 fps, and YouTube doesn't
       support high motion LDTV, SDTV, or EDTV
    3. `scale=` Set the video size, where `sws_flags=neighbor`
       specifies blocky resampling
* `-pix_fmt yuv420p`: Encode color (U and V chroma planes) smaller
  than full resolution.  Many web-based players require this.
  The pixel doubling to 288p ensures that this step loses no quality.
* `-ab`: Set AAC audio bitrate
* `-movflags +faststart`: Add an index to allow playback before the
  entire video downloads

The `\` means that the command continues on the next line.  This is a
feature of shells used on UNIX and Linux.  If using Windows Command
Prompt, delete the `\` at the end of each line and put the entire
command, from `ffmpeg` to `out.mp4`, on one line.

To change the pixel aspect ratio to the 8:7 of an NTSC Super Game
Boy, run two `scale` filters in a row.

    ffmpeg -y -i bgb-1567896789.avi -i bgb-1567896789.wav -r 30 \
      -vf 'scale=320:288:sws_flags=neighbor, scale=364:288:sws_flags=bilinear' \
      -pix_fmt yuv420p -ab 64000 -movflags +faststart out.mp4

This uses the `-r` option to reduce frame rate the simple way.

If your recording has an SGB border, or it is of an NES or Super NES
game captured at 256x224 pixels, change the sizes in the `scale`
commands to `512:448` and `584:448`.

Vertical video
--------------

If you're making a vertical video, and you want to insert a clip of a
Game Boy game with a frame that looks like a pixel art Game Boy Color:
```
ffmpeg -i bgb-1567896789.avi -i GB_shorts_border.png -i bgb-1567896789.wav -filter_complex \
  "[0]tblend=all_mode=average, framestep=2, scale=320:288:sws_flags=neighbor, pad=384:672:32:32[V]; [V][1]overlay" \
  -pix_fmt yuv420p -ab 96000 -movflags +faststart out.mp4
```

Consider alternating the GBC frame with close-ups using the
`crop` filter:
```
ffmpeg -i bgb-1567896789.avi -i bgb-1567896789.wav -t 47.5 -vf \
  "framestep=2, crop=96:144, scale=384:576:sws_flags=neighbor, pad=384:672" \
  -pix_fmt yuv420p -ab 96000 -movflags +faststart out.mp4
```


Further reading
---------------

* ["Editing videos with FFmpeg"](https://plutiedev.com/ffmpeg) on Plutiedev
