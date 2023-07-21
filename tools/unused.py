#!/usr/bin/env python3
"""
Long run detector for binary files
Copyright 2018 Damian Yerrick

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you must not
   claim that you wrote the original software. If you use this software
   in a product, an acknowledgment in the product documentation would be
   appreciated but is not required.
2. Altered source versions must be plainly marked as such, and must not be
   misrepresented as being the original software.
3. This notice may not be removed or altered from any source distribution.
"""
with open("libbet.gb", "rb") as infp:
    data = infp.read()

runthreshold = 32
runbyte, runlength, runs = 0xC9, 0, []
for addr, value in enumerate(data):
    if value != runbyte:
        if runlength >= runthreshold:
            runs.append((addr - runlength, addr))
        runbyte, runlength = value, 0
    runlength += 1
if runlength >= runthreshold:
    runs.append((len(data) - runlength, len(data)))

totalsz = 0
for startaddr, endaddr in runs:
    sz = endaddr - startaddr
    totalsz += sz
    print("%04x-%04x: %d" % (startaddr, endaddr - 1, sz))
print("total: %d bytes (%.1f KiB)" % (totalsz, totalsz / 1024.0))
