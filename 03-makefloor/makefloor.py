#!/usr/bin/env python3
"""
exploration of "make floor" for Libbet's game
Copyright 2018 Damian Yerrick

Definitions:

1. The field is a rectangle filled with tiles of four patterns
   [0, 1, 2, 3], arranged in a uniform random distribution.
   Its area is the number of tiles in the field.
2. A move is 1 or 2 tiles in +x, -x, +y, or -y direction from one
   tile to another, either of the same pattern or of the next pattern
   modulo 4.  A roll is 1 tile; a jump is 2 tiles.
3. The home position is at the center of the row at one end of the
   field, rounded if that row is of even length.  The back row is
   the row at the opposite end of the field.
4. A tile is reachable if a sequence of moves exists from home to
   that tile, and reverse reachable if a sequence of moves exists
   from that tile to the home position.  A tile is round trip
   reachable if it is both reachable and reverse reachable.
5. A move to a tile that is not reverse reachable causes the cursor
   to return to the home position.
6. A tile's score is the number of distinct directions in which a
   move from that tile can end up on a tile of the next pattern.
   A field's total score is the sum of all reachable tiles' scores.

Constraints:

1. [Nocash] A field's area must not exceed its total score.
2. [Pino] At least two tiles in the back row must be round trip
   reachable.
3. [Pino] At least half the tiles must be round trip reachable.
4. [Pino] The count of tiles of a given pattern must differ by no
   more than 1 from the count of tiles of a different pattern.

"""
import random
import sys
from collections import defaultdict, Counter

# Constructors ######################################################

def make_memoryless_field(w, h):
    return [bytearray(random.randrange(4) for x in range(w))
            for y in range(h)]

def make_shuffled_field(w, h):
    area = w * h
    field = bytearray(i % 4 for i in range(area))
    for i in range(area):
        r = random.randrange(32) % area
        field[i], field[r] = field[r], field[i]
    return [field[i:i + w] for i in range(0, area, w)]

constructors = [
    ('random', make_memoryless_field),
    ('even', make_shuffled_field),
]
fieldsizes = [
    (2, 8),
    (4, 4),
    (6, 4),
    (6, 6),
    (8, 6),
]

def print_hex_field(field):
    print("--"*len(field[0]))
    print("\n".join(row.hex() for row in field))

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

def print_color_field(field):
    out = []
    for row in field:
        out.append("".join(format_cell_top_half(cell) for cell in row))
        out.append("".join(format_cell_bottom_half(cell) for cell in row))
    print("\n".join(out))

# Reachability ######################################################

# right, hold right, left, hold left,
# up, hold up, down, hold down
movedests = [
    (1, 0), (2, 0), (-1, 0), (-2, 0),
    (0, -1), (0, -2), (0, 1), (0, 2),
]

def is_move_open(field, x, y, dircode, reverse=False):
    fromvalue = field[y][x] - (1 if reverse else 0)
    dx, dy = movedests[dircode]
    ytarget = y + dy
    if ytarget < 0 or ytarget >= len(field): return None
    row = field[ytarget]
    xtarget = x + dx
    if xtarget < 0 or xtarget >= len(row): return None
    diff = (row[xtarget] - fromvalue) & 0x03
    if diff >= 2: return None
    return xtarget, ytarget

NOT_RTR = 0x04
IS_DEADEND = 0x08
def find_reachable(field):
    """Modify a field in place to mark cells as not round trip reachable.

Return the count of round trip reachable cells.
"""
    ENTERED = 0x10
    CHECKED = 0x20
    RENTERED = 0x40
    RCHECKED = 0x80

    home_x = len(field[0]) // 2
    home_y = 0
    field[home_y][home_x] |= ENTERED | RENTERED

    # Recursively trace legal moves both forward and backward
    keepgoing = True
    while keepgoing:
        keepgoing = False
        for y in range(len(field)):
            for x in range(len(field[0])):
                if (field[y][x] & (ENTERED | CHECKED)) == ENTERED:
                    for dircode in range(len(movedests)):
                        target = is_move_open(field, x, y, dircode, 0)
                        if target:
                            tx, ty = target
                            field[ty][tx] |= ENTERED
                            keepgoing = True
                    field[y][x] |= CHECKED
                if (field[y][x] & (RENTERED | RCHECKED)) == RENTERED:
                    for dircode in range(len(movedests)):
                        target = is_move_open(field, x, y, dircode, 1)
                        if target:
                            tx, ty = target
                            field[ty][tx] |= RENTERED
                            keepgoing = True
                    field[y][x] |= RCHECKED

    # A tile that's not both round trip reachable is a trap door.
    # A move onto a trap door is legal, and in fact, Libbet must
    # take all possible moves onto or across trap doors in order
    # to complete the room.
    for row in field:
        for x in range(len(row)):
            c = row[x] & 0x03
            deadend_type = row[x] & (ENTERED | RENTERED)
            if deadend_type != ENTERED | RENTERED:
                c |= NOT_RTR
            if deadend_type == RENTERED:
                c |= IS_DEADEND
            row[x] = c

# Field statistics ##################################################

def calc_max_score(field, writeback=False):
    score = 0
    for y in range(len(field)):
        for x in range(len(field[0])):
            c = field[y][x]
            if c & NOT_RTR: continue
            dirs = 0
            for dircode in range(len(movedests)):
                pos = is_move_open(field, x, y, dircode)
                if not pos: continue
                xtarget, ytarget = pos
                # Only moves onto 
                destcolor = field[ytarget][xtarget]
                if ((c ^ destcolor) & 0x03) == 0: continue
                # Only unique directions from a tile score.
                # Both a roll and a hop in the same direction don't.
                dirs |= 0x10 << (dircode // 2)
            if writeback:
                field[y][x] = c | dirs
            while dirs:
                score += 1
                dirs &= dirs - 1
    return score

def get_field_stats(field):
    area = len(field) * len(field[0])
    rtr_area = sum(
        0 if c & NOT_RTR else 1
        for row in field
        for c in row
    )
    rtr_back_row = sum(
        0 if c & NOT_RTR else 1
        for c in field[-1]
    )
    deadend_area = sum(
        1 if c & IS_DEADEND else 0
        for row in field
        for c in row
    )
    return {
        'area': len(field) * len(field[0]),
        'rtr_area': rtr_area,
        'rtr_back_row': rtr_back_row,
        'deadend_area': deadend_area,
        'max_score': calc_max_score(field),
    }

def constraint_max_score(_, stats):
    return stats['max_score'] >= stats['area']

def constraint_reach_back_row(_, stats):
    """Return true if two tiles in the back row are round trip reachable."""
    return stats['rtr_back_row'] >= 2

def constraint_rtr_area(_, stats):
    return stats['rtr_area'] * 2 >= stats['area']

constraints = [
    ('score >= area', constraint_max_score),
    ('back reachable', constraint_reach_back_row),
    ('2*rtr >= area', constraint_rtr_area),
]

def make_field(w, h):
    field = None
    rejections = 0
    while field is None:
        field = make_memoryless_field(w, h)
        find_reachable(field)
        stats = get_field_stats(field)
        if not constraint_max_score(field, stats):
            field = None
            rejections += 1

    return field, stats['max_score'], rejections

def one_test():
    field, max_score, rejections = make_field(2, 8)
    if rejections:
        msg = ("Rejected %d fields" % rejections
               if rejections > 1
               else "Rejected one field")
        print(msg, file=sys.stderr)
    print_color_field(field)
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
    print("Generating %d rooms per combination of size and randomizer"
          % NUM_TRIALS)
    no_deadend_odds = {n: 1.0 for n, f in constructors}
    for w, h in fieldsizes:
        for buildname, buildfunc in constructors:
            allstats = defaultdict(list)
            constraintvalues = defaultdict(int)
            num_all_ok = num_all_ok_deadend = 0
            at_least_one_deadend = 1.0
            for i in range(NUM_TRIALS):
                field = buildfunc(w, h)
                find_reachable(field)
                stats = get_field_stats(field)
                allstatnames.update(stats)
                allstatnames.discard("area")
                for statname in allstatnames:
                    allstats[statname].append(stats[statname])
                all_ok = True
                for constraintname, constraintfunc in constraints:
                    ok = bool(constraintfunc(field, stats))
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

testfield = """
3001
2213
0103
3221
"""
arrowsymbols = "□→←↔↑↱↰↥↓↳↲↧↕↦↤+"

def solve(field):
    field = [bytearray(int(c) for c in row) for row in field.split()]
    find_reachable(field)
    s = calc_max_score(field, writeback=True)
    print("\n".join("".join(
        "○" if c & 0x08 else "◍" if c & 0x04 else arrowsymbols[c>>4]
        for c in row) for row in field))
    print("/%s" % s)

if __name__=='__main__':
    all_tests()
##    solve(testfield)
