#!/usr/bin/env python3
"""
experimental call graph reader for RGBASM

by Damian Yerrick
"""
import os, sys, argparse
from collections import defaultdict

SHOW_JUMP_ALWAYS = False

nonjump_opcodes = {
    'ld', 'add', 'adc', 'sub', 'sbc', 'xor', 'or', 'and', 'cp',
    'rlca', 'rla', 'rrca', 'rra', 'rlc', 'rl', 'rrc', 'rr',
    'swap', 'srl', 'sra', 'sla', 'bit', 'set', 'res',
    'ccf', 'scf', 'cpl', 'daa', 'di', 'ei', 'ret', 'reti',
    'dec', 'inc', 'ret', 'ldh', 'push', 'pop', 'nop', 'halt', 'stop',
}

def rgbint(s):
    if s.startswith('$'): return int(s[1:], 16)
    if s.startswith('%'): return int(s[1:], 2)
    return int(s[1:], 10)

class AsmFile(object):
    def __init__(self, lines=None):
        self.toplabel = self.jumptable_contents = None
        self.last_was_jump = False
        self.in_macro = self.in_jumptable = self.section_is_bss = False
        self.unknown_opcodes = set()
        self.exports = {}
        self.calls = defaultdict(set)
        self.tailcalls = defaultdict(set)
        self.linenum = 0
        self.warnings = []
        self.is_fixlabel = None
        if lines: self.extend(lines)

    def extend(self, lines):
        for line in lines: self.append(line)

    def append(self, line):
        self.linenum += 1
        line = line.strip().split(";", 1)[0]

        # Process labels
        label, line, is_exported = self.label_split(line)
        if label and not self.in_macro: self.add_label(label, is_exported)
        if not line: return

        # Handle some directives
        opcode, operands = self.opcode_split(line)
        if opcode == 'section':
            self.add_section(operands)
            return
        if opcode in ('export', 'global'):
            self.add_exports(operands)
            return
        if opcode == 'endm':
            if not self.in_macro:
                raise ValueError("endm without macro")
            self.in_macro = False
            return
        if opcode == 'macro':
            if self.in_macro:
                raise ValueError("nested macro not supported")
            self.in_macro = True
            self.unknown_opcodes.add(operands[0])
            return
        if opcode == 'jumptable':
            if self.toplabel is None:
                raise ValueError("jumptable without top-level label")
            self.in_jumptable = True
            return

        # Remaining opcodes add code if and only if they're
        # not inside a macro.
        if self.in_macro: return

        if opcode == 'dw':
            if self.in_macro: return
            if self.toplabel is None:
                raise ValueError("dw without top-level label")
            self.add_jumptable_entries(operands)
            return

        # Determine whether line is unconditional jump
        preserves_jump = self.opcode_preserves_jump_always(opcode, operands)
        is_jump = self.opcode_is_jump_always(opcode, operands)

        if self.opcode_can_jump(opcode):
            _, target = self.condition_split(operands)
            self.add_tailcall(self.toplabel, target)
        elif self.opcode_can_call(opcode):
            _, target = self.condition_split(operands)
            self.add_call(self.toplabel, target)
        elif opcode not in nonjump_opcodes and not preserves_jump:
            # Treat unknown opcodes as probably data macros defined
            # in an include file.  (The tool skips include files
            # because unlike in C and ca65, RGBASM include paths
            # are relative to the CWD, and the CWD is unknown.)
            if opcode not in self.unknown_opcodes:
                self.unknown_opcodes.add(opcode)
                self.warn("unknown instruction %s" % (opcode,))
            preserves_jump = True

        if not preserves_jump: self.last_was_jump = is_jump

    def add_label(self, label, is_exported=False):
        if label == '':
            self.warn("%s: disregarding anonymous label" % (self.toplabel,))
            return

        if label.startswith('.'):
            if self.toplabel is None:
                raise ValueError("no top-level label for local label %s"
                                 % (label,))
            label = self.toplabel + label
        else:
            if (self.toplabel is not None and not self.section_is_bss
                and not self.last_was_jump and self.last_was_jump is not None):
                if self.is_fixlabel:
                    self.warn("fixlabel %s falls through to %s"
                              % (self.toplabel, label))
                    self.add_tailcall(self.toplabel, label)
                    self.is_fixlabel = False
                else:
                    self.warn("%s may fall through to %s"
                              % (self.toplabel, label))
            self.flush_jumptable()
            self.toplabel = label
            self.last_was_jump = None

        if is_exported: self.add_exports([label])

    def warn(self, msg):
        self.warnings.append((self.linenum, msg))

    def add_exports(self, new_exports):
        for label in new_exports:
            self.exports[label] = self.linenum

    def add_section(self, operands):
        if len(operands) < 2:
            raise ValueError("section %s has no memory area!")
        if (self.toplabel is not None and not self.section_is_bss
            and not self.last_was_jump and self.last_was_jump is not None):
            self.warn("%s may fall off end of section" % (self.toplabel,))
        self.flush_jumptable()
        self.toplabel = None
        self.last_was_jump = True
        self.is_fixlabel = False
        op1split = operands[1].split('[', 1)
        memory_area = op1split[0].strip().upper()
        ramsection_names = ("WRAM", "SRAM", "HRAM")
        self.section_is_bss = memory_area.startswith(ramsection_names)

        # Try to assign fixed memory addresses, so as to find things like
        # RST $00, $08, $10, ..., $38, and entry point at $100
        fixaddr = op1split[1].rstrip(']').strip() if len(op1split) > 1 else ''
        if fixaddr and memory_area == "ROM0":
            fixlabel = self.canonicalize_call_target(fixaddr)
            self.add_label(fixlabel)
            self.add_exports([fixlabel])
            self.is_fixlabel = True

    def flush_jumptable(self):
        """Have the current toplabel tailcall all jumptable_contents members.

Call this before setting or clearing a toplabel.
"""
        if self.toplabel is not None and self.in_jumptable:
            for row in self.jumptable_contents:
                self.add_tailcall(self.toplabel, row)
        self.in_jumptable, self.jumptable_contents = False, set()

    def add_call(self, fromlabel, tolabel):
        # disregard calls within function
        if tolabel.startswith('.'): return

        self.calls[fromlabel].add(self.canonicalize_call_target(tolabel))

    def add_tailcall(self, fromlabel, tolabel):
        # disregard jumps within function
        if tolabel.startswith((':', '.')): return
        # disregard whole-function loops
        if tolabel == fromlabel: return
        # jp hl is handled by "tailcalls some_table"
        if tolabel.lower() == 'hl': return

        self.tailcalls[fromlabel].add(self.canonicalize_call_target(tolabel))

    def add_jumptable_entries(self, operands):
        self.jumptable_contents.update(operands)

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
            'warn', 'fail'
        )
        if opcode in ignored_opcodes: return True
        return False

    @staticmethod
    def opcode_is_jump_always(opcode, operands):
        """Return true if the following line is never reachable from this line"""
        return_opcodes = ('ret', 'reti')
        jump_opcodes = ('jp', 'jr', 'fallthrough')
        is_conditional, target = AsmFile.condition_split(operands)
        if is_conditional: return False
        if opcode in return_opcodes or opcode in jump_opcodes: return True
        return False

    @staticmethod
    def opcode_can_jump(opcode):
        return opcode in ('jp', 'jr', 'tailcalls', 'fallthrough')

    @staticmethod
    def opcode_can_call(opcode):
        return opcode in ('call', 'rst', 'calls')

    @staticmethod
    def canonicalize_call_target(target):
        """Convert numbers used as call targets to 4-digit hex.

Convert '56' and '$38' to '$0038', and leave non-numbers unchanged.
""" 
        try:
            fixlabel = rgbint(target)
        except ValueError:
            return target
        else:
            return "$%04X" % fixlabel

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

def parse_argv(argv):
    p = argparse.ArgumentParser(description="Parses RGBASM source to determine a call graph")
    p.add_argument("sourcefile", nargs="+",
                   help="name of source code file")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="print more debugging information")
    return p.parse_args(argv[1:])

def main(argv=None):
    args = parse_argv(argv or sys.argv)
    files = {}
    all_errors, all_warnings = [], []
    for filename in args.sourcefile:
        with open(filename, "r") as infp:
            result = AsmFile()
            try:
                result.extend(infp)
            except Exception as e:
                if args.verbose:
                    from traceback import print_exc
                    print_exc()
                all_errors.append(filename, result.linenum, str(e))
            else:
                files[filename] = result
            finally:
                all_warnings.extend((filename, ln, msg)
                                    for ln, msg in result.warnings)

    all_exports = {}  # {symbol: (filename, linenum), ...}
    for filename, result in files.items():
        for symbol, linenum in result.exports.items():
            try:
                old_filename, old_linenum = all_exports[symbol]
            except KeyError:
                all_exports[symbol] = filename, linenum
            else:
                all_errors.append((filename, linenum, "%s reexported" % symbol))
                all_errors.append((old_filename, old_linenum,
                                   "%s had been exported here" % symbol))

##    print("root:", all_exports['$0100'])

    if all_errors:
        print("\n".join(
            "%s:%d: error: %s" % row for row in all_warnings
        ), file=sys.stderr)
    if all_warnings:
        print("\n".join(
            "%s:%d: warning: %s" % row for row in all_warnings
        ), file=sys.stderr)

if __name__=='__main__':
    if 'idlelib' in sys.modules:
        folder = "../src"
        args = ["./callgraph.py"]
        args.extend(os.path.join(folder, file)
                    for file in sorted(os.listdir(folder))
                    if os.path.splitext(file)[1].lower()
                    in ('.z80', '.asm', '.s', '.inc'))
        main(args)
    else:
        main()
