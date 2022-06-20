Practical audio representation for Game Boy
===========================================

A few NES games use its limited hardware envelope support, such as
Tengen's _Klax_.  Most games use software volume control instead,
calculationg a volume 50 to 60 times per second and writing it to
the sound circuit's registers.  A sound effect can be described with
2 bytes per frame: one for pitch and one for timbre and volume.
Pently, an NES audio driver by Damian Yerrick, has used the
following format for sound effects and drums since 2009 and
instrument attacks since 2014.

    FEDC BA98 7654 3210
    |||| |||| ||   ++++- Volume
    |||| |||| ++-------- Timbre (pulse)
    |+++-++++----------- Pitch
    +------------------- Timbre (noise)

Game Boy is somewhat different, as its hardware envelope is both
more flexible and required.  It allows starting at any volume and
optionally increasing or decreasing by one unit every 1-7 frames.
An ongoing note's envelope cannot be changed, and starting a new note
incurs a 2 ms jitter in the output.  So to minimize hiccups, the
volume envelope of a sound effect or instrument has to be defined
with piecewise linear segments, so that hiccups occur only between
one segment and the next.

Proposed format
---------------
A sound effect's bytestream then becomes a list of segments.

Each segment has a first parameter, a duration, optionally a pitch
change, and optionally an envelope change.

    7654 3210  Segment header ($00-$EF)
    |||| ++++- segment duration (0: 1 frame; 15: 16 frames)
    |||+------ 1: pitch change follows
    ||+------- 1: deep parameter follows
    ++-------- quick parameter

If deep parameter and pitch change are used together, deep parameter
comes first.

### Pulse

For the pulse channels, the quick parameter is duty (1/8, 1/4, 1/2),
written to FF11, FF16 D7-6.  Quick parameter value 3 (3/4 duty) is
not used because it sounds the same as value 1 (1/4 duty).

Deep parameter for pulse or noise controls the volume envelope
via FF12, FF17, or FF21.

    7654 3210  Pulse/noise deep parameter: Envelope
    |||| ||||
    |||| |+++- Decay period (0: no decay; 1-7: frames per change)
    |||| +---- Decay direction (0: -1; 1: +1)
    ++++------ Starting volume (0: mute; 1-15: linear)

Though frames in the segment header are 59.73 Hz, frames to the
envelope unit are 64.00 Hz, not 59.73 Hz.  Ideally, listeners
should not notice the difference.

For sound effects, pitch is an offset in semitones above the lowest
supported pitch, which is low C (65.4 Hz).  For instruments, pitch
is a signed offset above or below the note's pitch.

### Wave

For the wave channel, the quick parameter is volume (1, 1/2, 1/4,
mute), written to FF1C D6-5.  The value in the instrument is one
less than that actually written to FF1C, such that value 3 mutes
the channel.

Wave deep parameter is an index into a 4096-byte block of wavetables,
each 16 bytes long with 2 samples per byte.

Though the wave channel's playback rate is twice as fast as that
of the pulse channel, the waveform is four times as long: 32 samples
instead of 8.  This makes a given pitch value play one octave lower
than the same pitch value on the pulse channel.

### Noise

Noise does not use quick parameter, and its deep parameter is the
same as that of pulse.

Noise is a linear feedback shift register whose clock rate is
controlled by two dividers on a 524.3 kHz clock: one a power of two
and one usually set between 8 and 14.  Thus the noise output has a
sample rate of `2^(19 - s) / r` Hz.

    7654 3210  Noise pitch parameter
    |||| |+++- Period divider r (1, 2, 4, 6, 8, 10, 12, 14)
    |||| +---- Periodic flag (0: 32767 steps, more noise-like;
    ||||       1: 127 steps; more tone-like)
    ++++------ Period prescaler s

With periodic mode on, the eight divider values produce notes close
to C, C, C, F, C, G#, F, and D respectively.

Be careful when switching the periodic flag from 0 to 1.  There are
cases when this causes the LFSR to get stuck, and emulators don't
always emulate this.

Conflicts
---------
Quick parameter value 3, deep parameter, and pitch change should not
be used in the same segment, as segment header codes $F0-$FF are
reserved.  This is why quick parameters are assigned such that either
3 is not used or not used with a deep parameter.  Pulse duty 3 is
redundant, and muted triangle needs no wave or pitch change.

Showing it off
--------------
A GIF is inadequate when asking for feedback on sound effects.
Fortunately, bgb can save audio to an uncompressed wave file
and video in whatever VFW codec is installed.

    ffmpeg -i bgb-1540876262.avi -i bgb-1540876262.wav \
      -s 320x288 -sws_flags neighbor -pix_fmt yuv420p \
      libbet.mp4
