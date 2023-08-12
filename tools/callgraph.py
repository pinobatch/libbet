#!/usr/bin/env python3
"""
experimental call graph reader for RGBASM

by Damian Yerrick
"""
import os, sys, argparse
from collections import defaultdict

SHOW_JUMP_ALWAYS = False

class AsmFile(object):
    def __init__(self, lines=None):
        self.toplabel = None
        self.last_was_jump = False
        self.section_is_bss = False
        self.seen_nonjump_opcodes = {
            'ld', 'add', 'adc', 'sub', 'sbc', 'xor', 'or', 'and', 'cp',
            'rlca', 'rla', 'rrca', 'rra', 'rlc', 'rl', 'rrc', 'rr',
            'swap', 'srl', 'sra', 'sla', 'bit', 'set', 'res',
            'ccf', 'scf', 'cpl', 'daa', 'di', 'ei', 'ret', 'reti',
            'dec', 'inc', 'ret', 'ldh', 'push', 'pop', 'nop', 'halt', 'stop',
        }
        self.exports = set()
        self.calls = defaultdict(set)
        self.tailcalls = defaultdict(set)
        self.linenum = 0
        self.warnings = []
        if lines: self.extend(lines)

    def extend(self, lines):
        for line in lines: self.append(line)

    def append(self, line):
        self.linenum += 1
        line = line.strip().split(";", 1)[0]

        # Process labels
        label, line, is_exported = self.label_split(line)
        if label: self.add_label(label, is_exported)
        if not line: return

        # Determine whether line is unconditional jump
        opcode, operands = self.opcode_split(line)
        if opcode == 'section':
            self.add_section(operands)
            return
        if opcode in ('export', 'global'):
            self.exports.update(operands)
            return

        preserves_jump = self.opcode_preserves_jump_always(opcode, operands)
        is_jump = self.opcode_is_jump_always(opcode, operands)
        if SHOW_JUMP_ALWAYS and not self.section_is_bss:
            print("%d: note: %s %s %s jump always"
                  % (self.linenum, opcode, operands,
                     "preserves" if preserves_jump
                     else "is" if is_jump else "is not"),
                     file=sys.stderr)

        if self.opcode_can_jump(opcode):
            _, target = self.condition_split(operands)
            self.add_tailcall(self.toplabel, target)
        elif self.opcode_can_call(opcode):
            _, target = self.condition_split(operands)
            self.add_call(self.toplabel, target)
        else:
            if (opcode not in self.seen_nonjump_opcodes
                and not preserves_jump):
                self.seen_nonjump_opcodes.add(opcode)
                print("%d: note: %s not jump or call"
                      % (self.linenum, opcode), file=sys.stderr)

        if not preserves_jump: self.last_was_jump = is_jump

    def add_label(self, label, is_exported=False):
        if label == '':
            print("%d: %s: disregarding anonymous label"
                  % (self.linenum, self.toplabel), file=sys.stderr)
            return

        if label.startswith('.'):
            if self.toplabel is None:
                raise ValueError("no top-level label for local label %s"
                                 % (label,))
            label = self.toplabel + label
        else:
            if (self.toplabel is not None and not self.last_was_jump
                and not self.section_is_bss):
                print("%d: warning: %s may fall through to %s"
                      % (self.linenum, self.toplabel, label), file=sys.stderr)
            self.toplabel = label

        if is_exported: self.exports.add(label)

    def add_section(self, operands):
        if len(operands) < 2:
            raise ValueError("section %s has no memory area!")
        if (self.toplabel is not None and not self.last_was_jump
            and not self.section_is_bss):
            print("%d: warning: %s may fall off end of section"
                  % (self.linenum, self.toplabel), file=sys.stderr)

        self.toplabel = None
        self.last_was_jump = True
        memory_area = operands[1].split('[', 1)[0].strip().upper()
        ramsection_names = ("WRAM", "SRAM", "HRAM")
        self.section_is_bss = memory_area.startswith(ramsection_names)

    def add_call(self, fromlabel, tolabel):
        # disregard calls within function
        if tolabel.startswith('.'): return

        self.tailcalls[fromlabel].add(tolabel)

    def add_tailcall(self, fromlabel, tolabel):
        # disregard jumps within function
        if tolabel.startswith((':', '.')): return
        # disregard whole-function loops
        if tolabel == fromlabel: return

        self.tailcalls[fromlabel].add(tolabel)

    @staticmethod
    def label_split(line):
        """Split a line into label and remainder parts

Return (label part, remainder part, True if exported)
"""
        colonsplit = line.split(':', 1)
        if '"' in colonsplit[0]: return None, line, False  # ld a, ":"
        if len(colonsplit) == 1 and line.startswith('.'):
            # local labels can be terminated by whitespace instead of colon
            colonsplit = line.split(None, 1)
            if len(colonsplit) < 2: return line, "", False
        if len(colonsplit) < 2: return None, line, False

        label, line = colonsplit
        is_exported = line.startswith(':')
        if is_exported: line = line[1:]
        return label.rstrip(), line.lstrip(), is_exported

    @staticmethod
    def opcode_split(line):
        """Split a line into opcode and operand parts

line must not define a label, that is, label_split must be run first

Return (opcode, [operand, ...])
"""
        first2words = line.split(None, 1)
        opcode = first2words[0].lower()
        operands = first2words[1] if len(first2words) > 1 else ''
        return opcode, [x.strip() for x in operands.split(',')]

    @staticmethod
    def opcode_preserves_jump_always(opcode, operands):
        """Return true if this line usually doesn't affect function-to-function reachability"""
        ignored_opcodes = (
            'if', 'else', 'elif', 'endc', 'def', 'include', 'incbin',
            'rept', 'endr', 'dw', 'db', 'ds', 'rsreset', 'rsset', 'assert',
        )
        if opcode in ignored_opcodes: return True
        return False

    @staticmethod
    def opcode_is_jump_always(opcode, operands):
        """Return true if the following line is never reachable from this line"""
        return_opcodes = ('ret', 'reti')
        jump_opcodes = ('jp', 'jr')
        is_conditional, target = AsmFile.condition_split(operands)
        if is_conditional: return False
        if opcode in return_opcodes or opcode in jump_opcodes: return True
        return False

    @staticmethod
    def opcode_can_jump(opcode):
        return opcode in ('jp', 'jr', 'tailcalls', 'fallthrough')

    @staticmethod
    def opcode_can_call(opcode):
        return opcode in ('call', 'calls')

    @staticmethod
    def condition_split(operands):
        condition_codes = ('c', 'nc', 'z', 'nz')
        is_conditional = (len(operands) > 0
                          and operands[0].lower() in condition_codes)
        target_operand = 1 if is_conditional else 0
        target = (operands[target_operand]
                  if len(operands) > target_operand
                  else '')
        return is_conditional, target

def load_file(lines):
    toplabel = None
    exported_labels = set()
    for linenum, line in enumerate(lines):
        line = line.strip()
        line = line
        colonsplit = line.split(':', 1)
        if len(colonsplit) == 1 and line.startswith('.'):
            # local labels can be terminated by whitespace instead of colon
            colonsplit = line.split(None, 1)
        if len(colonsplit) > 1:
            label, line = colonsplit
            label = label.strip()
            if label.startswith(':'):
                print("%d: disregarding anonymous label %s in %s"
                      % (linenum + 1, label, toplabel))
            else:
                if label.startswith('.'):
                    if toplabel is None:
                        raise ValueError("%d: no top-level label for local label %s"
                                         % (linenum + 1, label))
                    label = toplabel + label
                else:
                    toplabel = label
                print("label", label)
                is_exported = line.startswith(':')
                if is_exported:
                    line = line[1:]
                    exported_labels.add(label)
                    print("export %s" % label)
        if not line: continue
        print("line of code", repr(line))

def parse_argv(argv):
    p = argparse.ArgumentParser(description="Parses RGBASM source to determine a call graph")
    p.add_argument("sourcefile", nargs="+",
                   help="name of source code file")
    return p.parse_args(argv[1:])

def main(argv=None):
    args = parse_argv(argv or sys.argv)
    for filename in args.sourcefile:
        print("parsing %s" % filename, file=sys.stderr)
        with open(filename, "r") as infp:
            result = AsmFile(infp)

if __name__=='__main__':
    if 'idlelib' in sys.modules:
        main("""./callgraph.py
../src/main.z80
""".split())
    else:
        main()
