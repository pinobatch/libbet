#!/usr/bin/env python3
"""
exploration of "make floor" for Libbet's game
Copyright 2018 Damian Yerrick

Definitions:

1. The floor is a rectangle filled with cells of four patterns
   [0, 1, 2, 3], arranged in a uniform random distribution.
   Its area is the number of cells in the floor.
2. A move is 1 or 2 cells in +x, -x, +y, or -y direction from one
   cell to another, either of the same pattern or of the next pattern
   modulo 4.  A roll is 1 cell; a jump is 2 cells.
3. The home position is at the center of the row at one end of the
   floor, rounded if that row is of even length.  The back row is
   the row at the opposite end of the floor.
4. A cell is reachable if a sequence of moves exists from home to
   that cell, and reverse reachable if a sequence of moves exists
   from that cell to the home position.  A cell is round trip
   reachable if it is both reachable and reverse reachable.
5. A move to a cell that is not reverse reachable causes the cursor
   to return to the home position.
6. A cell's score is the number of distinct directions in which a
   move from that cell can end up on a cell of the next pattern.
   A floor's total score is the sum of all reachable cells' scores.

Constraints:

1. [Nocash] A floor's area must not exceed its total score.
2. [Pino] At least two cells in the back row must be round trip
   reachable.
3. [Pino] At least half the cells must be round trip reachable.
4. [Pino] The count of cells of a given pattern must differ by no
   more than 1 from the count of cells of a different pattern.

"""
import random
import sys
from collections import defaultdict, Counter

# Constructors ######################################################

def make_memoryless_floor(w, h):
    return [bytearray(random.randrange(4) for x in range(w))
            for y in range(h)]

def make_shuffled_floor(w, h):
    area = w * h
    floor = bytearray(i % 4 for i in range(area))
    for i in range(area):
        r = random.randrange(32) % area
        floor[i], floor[r] = floor[r], floor[i]
    return [floor[i:i + w] for i in range(0, area, w)]

constructors = [
    ('random', make_memoryless_floor),
    ('even', make_shuffled_floor),
]
floorsizes = [
    (2, 8),
    (4, 4),
    (6, 4),
    (6, 6),
    (8, 6),
]

def print_hex_floor(floor, outfp=None):
    print("--"*len(floor[0]))
    print("\n".join(row.hex() for row in floor), file=outfp or sys.stdout)

def format_cell_top_half(cell):
    symbols = "▓▒░ "
    return symbols[cell & 0x03]*4

def format_cell_bottom_half(cell):
    symbols = "▓▒░ "
    trapdoorsymbol = "██"
    c = symbols[cell & 0x03]
    if cell & 0x04:
        return "".join((c, trapdoorsymbol, c))
    else:
        return c * 4

def print_color_floor(floor, outfp=None):
    out = []
    for row in floor:
        out.append("".join(format_cell_top_half(cell) for cell in row))
        out.append("".join(format_cell_bottom_half(cell) for cell in row))
    print("\n".join(out), file=outfp or sys.stdout)

# Reachability ######################################################

# right, hold right, left, hold left,
# up, hold up, down, hold down
movedests = [
    (1, 0), (2, 0), (-1, 0), (-2, 0),
    (0, -1), (0, -2), (0, 1), (0, 2),
]

def is_move_open(floor, x, y, dircode, reverse=False):
    fromvalue = floor[y][x] - (1 if reverse else 0)
    dx, dy = movedests[dircode]
    ytarget = y + dy
    if ytarget < 0 or ytarget >= len(floor): return None
    row = floor[ytarget]
    xtarget = x + dx
    if xtarget < 0 or xtarget >= len(row): return None
    diff = (row[xtarget] - fromvalue) & 0x03
    if diff >= 2: return None
    return xtarget, ytarget

NOT_RTR = 0x04
IS_DEADEND = 0x08
def find_reachable(floor, bidi=False):
    """Modify a floor in place to mark cells as not round trip reachable.

Return the count of passes needed.
"""
    ENTERED = 0x10
    CHECKED = 0x20
    RENTERED = 0x40
    RCHECKED = 0x80

    home_x = len(floor[0]) // 2
    home_y = 0
    floor[home_y][home_x] |= ENTERED | RENTERED

    # Recursively trace legal moves both forward and backward
    keepgoing, passes = True, 0
    while keepgoing:
        keepgoing = False
        # TODO: To speed propagation of ENTERED/RENTERED to lower-
        # numbered rows, consider traversing Y in opposite directions
        # each pass.
        # https://en.wikipedia.org/wiki/Cocktail_shaker_sort
        xseq, yseq = range(len(floor[0])), range(len(floor))
        if bidi and (passes & 1):
            xseq, yseq = xseq[::-1], yseq[::-1]
        for y in yseq:
            for x in xseq:
                if (floor[y][x] & (ENTERED | CHECKED)) == ENTERED:
                    for dircode in range(len(movedests)):
                        target = is_move_open(floor, x, y, dircode, 0)
                        if target:
                            tx, ty = target
                            floor[ty][tx] |= ENTERED
                            keepgoing = True
                    floor[y][x] |= CHECKED
                if (floor[y][x] & (RENTERED | RCHECKED)) == RENTERED:
                    for dircode in range(len(movedests)):
                        target = is_move_open(floor, x, y, dircode, 1)
                        if target:
                            tx, ty = target
                            floor[ty][tx] |= RENTERED
                            keepgoing = True
                    floor[y][x] |= RCHECKED
        passes += 1

    # A cell that's not both round trip reachable is a trap door.
    # A move onto a trap door is legal, and in fact, Libbet must
    # take all possible moves onto or across trap doors in order
    # to complete the floor.
    for row in floor:
        for x in range(len(row)):
            c = row[x] & 0x03
            deadend_type = row[x] & (ENTERED | RENTERED)
            if deadend_type != ENTERED | RENTERED:
                c |= NOT_RTR
            if deadend_type == RENTERED:
                c |= IS_DEADEND
            row[x] = c

    return passes

# floor statistics ##################################################

def calc_max_score(floor, writeback=False):
    score = 0
    for y in range(len(floor)):
        for x in range(len(floor[0])):
            c = floor[y][x]
            if c & NOT_RTR: continue
            dirs = 0
            for dircode in range(len(movedests)):
                pos = is_move_open(floor, x, y, dircode)
                if not pos: continue
                xtarget, ytarget = pos
                # Only moves onto 
                destcolor = floor[ytarget][xtarget]
                if ((c ^ destcolor) & 0x03) == 0: continue
                # Only unique directions from a cell score.
                # Both a roll and a hop in the same direction don't.
                dirs |= 0x10 << (dircode // 2)
            if writeback:
                floor[y][x] = c | dirs
            while dirs:
                score += 1
                dirs &= dirs - 1
    return score

def get_floor_stats(floor):
    area = len(floor) * len(floor[0])
    rtr_area = sum(
        0 if c & NOT_RTR else 1
        for row in floor
        for c in row
    )
    rtr_back_row = sum(
        0 if c & NOT_RTR else 1
        for c in floor[-1]
    )
    deadend_area = sum(
        1 if c & IS_DEADEND else 0
        for row in floor
        for c in row
    )
    return {
        'area': len(floor) * len(floor[0]),
        'rtr_area': rtr_area,
        'rtr_back_row': rtr_back_row,
        'deadend_area': deadend_area,
        'max_score': calc_max_score(floor),
    }

def constraint_max_score(_, stats):
    return stats['max_score'] >= stats['area']

def constraint_reach_back_row(_, stats):
    """Return true if two cells in the back row are round trip reachable."""
    return stats['rtr_back_row'] >= 2

def constraint_rtr_area(_, stats):
    return stats['rtr_area'] * 2 >= stats['area']

constraints = [
    ('score >= area', constraint_max_score),
    ('back reachable', constraint_reach_back_row),
    ('2*rtr >= area', constraint_rtr_area),
]

def make_floor(w, h):
    floor = None
    rejections = flood_passes = 0
    while floor is None:
        floor = make_memoryless_floor(w, h)
        floorcopy = [bytearray(row) for row in floor]
        npasses = find_reachable(floorcopy, False)
        npasses = find_reachable(floor, True)
        flood_passes += npasses
        if floorcopy != floor:
            print("Floor MISMATCH!", file=sys.stderr)
            print_color_floor(floor, file=sys.stderr)
            print_color_floor(floorcopy, file=sys.stderr)
            print(repr(floor), file=sys.stderr)
            print(repr(floorcopy), file=sys.stderr)
        assert floorcopy == floor
        stats = get_floor_stats(floor)
        if not constraint_max_score(floor, stats):
            floor = None
            rejections += 1

    return floor, stats['max_score'], rejections, flood_passes

def one_test():
    floor, max_score, rejections, flood_passes = make_floor(2, 8)
    print("Flood fill used %d passes" % flood_passes, file=sys.stderr)
    if rejections:
        print("Rejected %d floors" % rejections
              if rejections > 1
              else "rejected one floor", file=sys.stderr)
    print_color_floor(floor)
    print("SCORE: 00/%d" % max_score)

def key_vigintiles(seq):
    """Return 5th, 25th, 50th, 75th, and 95th percentiles"""
    seq = sorted(seq)
    f = [seq[len(seq) * d // 20] for d in [1, 5, 10, 15, 19]]
    f.append(seq[-1])
    return f

vigintiles_names = ["5% <=", "25% <=", "50% <=", "75% <=", "95% <=", "max"]

def all_tests():
    allstatnames = set()
    NUM_TRIALS = 3000
    print("Generating %d floors per combination of size and randomizer"
          % NUM_TRIALS)
    no_deadend_odds = {n: 1.0 for n, f in constructors}
    for w, h in floorsizes:
        for buildname, buildfunc in constructors:
            allstats = defaultdict(list)
            constraintvalues = defaultdict(int)
            num_all_ok = num_all_ok_deadend = 0
            at_least_one_deadend = 1.0
            for i in range(NUM_TRIALS):
                floor = buildfunc(w, h)
                floorcopy = [bytearray(row) for row in floor]
                flood_passes = find_reachable(floorcopy, False)
                allstats['flood_passes'].append(flood_passes)
                flood_passes = find_reachable(floor, True)
                allstats['flood_passes_bidi'].append(flood_passes)
                stats = get_floor_stats(floor)
                allstatnames.update(stats)
                allstatnames.discard("area")
                for statname in allstatnames:
                    allstats[statname].append(stats[statname])
                all_ok = True
                for constraintname, constraintfunc in constraints:
                    ok = bool(constraintfunc(floor, stats))
                    all_ok = all_ok and ok
                    if ok:
                        constraintvalues[constraintname] += 1
                if all_ok:
                    num_all_ok += 1
                    if stats['deadend_area'] > 0:
                        num_all_ok_deadend += 1

            no_deadend_odds[buildname] *= 1 - (num_all_ok_deadend / num_all_ok)
            vigs = sorted((n, key_vigintiles(v)) for n, v in allstats.items())

            # Compose report for this stat
            lines = [
                "%dx%d %s" % (w, h, buildname),
                "area: %d" % (w * h,)
            ]
            lines.extend(
                "%s: %s" % (name, ", ".join(
                    "%s %s" % (n, v) for n, v in zip(vigintiles_names, values)
                ))
                for name, values in vigs
            )
            lines.extend(
                "%s: %.1f%%"
                % (n, constraintvalues[n] * 100 / NUM_TRIALS)
                for n, _ in constraints
            )
            lines.append("all: %.1f%%" % (num_all_ok * 100 / NUM_TRIALS,))
            lines.append("dead end among ok: %.1f%%"
                         % (num_all_ok_deadend * 100 / num_all_ok,))
            lines.append("at least 1 dead end so far: %.1f%%"
                         % ((1 - no_deadend_odds[buildname]) * 100,))
            print("\n  ".join(lines))

# Cheating ##########################################################

testfloor = """
3001
2213
0103
3221
"""
arrowsymbols = "□→←↔↑↱↰↥↓↳↲↧↕↦↤+"

def solve(floor):
    floor = [bytearray(int(c) for c in row) for row in floor.split()]
    find_reachable(floor)
    s = calc_max_score(floor, writeback=True)
    print("\n".join("".join(
        "○" if c & 0x08 else "◍" if c & 0x04 else arrowsymbols[c>>4]
        for c in row) for row in floor))
    print("/%s" % s)

if __name__=='__main__':
    all_tests()
##    solve(testfloor)
