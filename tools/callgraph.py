#!/usr/bin/env python3
"""
experimental call graph reader for RGBASM

by Damian Yerrick
"""
import os, sys, argparse
from collections import defaultdict
from itertools import chain

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
        self.locals_size = {}  # {funcname: {varname: size, ...}, ...}
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

        if opcode == 'local':
            self.add_local(operands)
            return

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
            # since https://github.com/gbdev/rgbds/pull/1159
            # a local label may appear outside the scope of the
            # corresponding global label, for an "in medias res"
            # routine like stpcpy
            label = label.split(".")[0]
            if (self.toplabel is not None and not self.section_is_bss
                and not self.last_was_jump and self.last_was_jump is not None):
                if self.is_fixlabel:
                    self.warn("fixed address label %s falls through to %s"
                              % (self.toplabel, label))
                    self.add_tailcall(self.toplabel, label)
                    self.is_fixlabel = False
                elif self.toplabel != label:
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

    def end_section(self):
        """Perform tasks at the end of a section.

Make sure to call this after appending all lines from a file.
Otherwise, a jump table that occurs last may not be found.
"""
        if (self.toplabel is not None and not self.section_is_bss
            and not self.last_was_jump and self.last_was_jump is not None):
            self.warn("%s may fall off end of section" % (self.toplabel,))
        self.flush_jumptable()
        self.toplabel = None
        self.last_was_jump = True
        self.is_fixlabel = False

    def add_section(self, operands):
        if len(operands) < 2:
            raise ValueError("section %s has no memory area!")
        self.end_section()

        # Determine whether this is a RAM section.  RAM sections
        # don't issue fallthrough warnings.
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

    def add_local(self, operands):
        varname = operands[0]
        if self.toplabel is None:
            raise ValueError("local %s without top-level label" % (varname,))
        function_locals = self.locals_size.setdefault(self.toplabel, {})
        try:
            size = function_locals[varname]
        except KeyError:
            size = operands[1] if len(operands) > 1 else ''
            function_locals[varname] = size = int(size or '1')
        else:
            raise ValueError("redefined local %s; previous size was %d"
                             % (varname, size))

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
        """Convert numbers used as call targets to 4-digit hex and remove sub-labels.

Convert '56' and '$38' to '$0038' and 'routine.loop' to 'routine'.
""" 
        try:
            fixlabel = rgbint(target)
        except ValueError:
            # treat a call to a sub-label as a call to its top label
            s = target.split('.', 1)
            return s[0] or target
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

def load_files(filenames, verbose=False):
    """Load and parse source code files.

filenames -- iterable of things to open()
verbose -- if True, print exception stack traces to stderr

Return a 2-tuple (files, all_errors, all_warnings)
- files -- {filename: AsmFile instance, ...}
- all_errors -- [(filename, linenum, msg), ...] of exceptions
- all_warnings -- (filename, linenum, msg), ...] of warnings
"""
    if verbose:
        from traceback import print_exc

    files, all_errors, all_warnings = {}, [], []
    for filename in filenames:
        with open(filename, "r") as infp:
            result = AsmFile()
            try:
                result.extend(infp)
                result.end_section()
            except Exception as e:
                if verbose: print_exc()
                all_errors.append((filename, result.linenum, str(e)))
            else:
                files[filename] = result
            finally:
                all_warnings.extend((filename, ln, msg)
                                    for ln, msg in result.warnings)
    return files, all_errors, all_warnings

def get_exports(files):
    """Find exports in a set of parsed source files.

files -- {filename: AsmFile instance, ...}

Return a 2-tuple (exports, errors)
exports -- {symbol: (filename, linenum), ...}
errors -- [(filename, linenum, msg), ...]
"""
    all_exports, all_errors = {}, []
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
    return all_exports, all_errors

# TODO: see if changing the toposort from postorder to breadth-first search
# would help the core usage

def postorder_callees(files, exports, start_label="$0100"):
    """Sort labels reachable from the start by callees first.

files: a dict {filename: AsmFile instance, ...}
exports: a dict {label: (filename, ...), ...}
start_label: the first label to call (in GB, usually $0100)

Return (toposort, itoposort)
where toposort is [(filename, label), ...]
and itoposort is its inverse {(filename, label): index into toposort, ...}
"""
    # stack is a list of stack frames to be visited
    # each stack frame is [(module, label), ...]
    stack = [[(exports[start_label][0], start_label)]]
    itoposort = {}  # {(filename, label): index, ...}
    while stack:
        stackframe = stack.pop()
        routine_key = stackframe[-1]
        filename, label = routine_key
        assert filename is not None
        if routine_key in itoposort: continue

        # Find all callees that aren't already in the toposort
        # or in the stack
        module = files[filename]
        callees = module.calls[label]
        tailcallees = module.tailcalls[label]
        new_callees = []
        for callee in chain(callees, tailcallees):
            try:
                callee_filename = exports[callee]
            except KeyError:
                callee_filename = filename
            else:
                callee_filename = callee_filename[0]
            callee_key = callee_filename, callee
            if callee_key not in itoposort and callee_key not in stackframe:
                new_callees.append(callee_key)

        # If any callee hasn't been seen, toposort all callees first
        # and come back later
        if new_callees:
            stack.append(stackframe)
            for callee in new_callees:
                new_frame = list(stackframe)
                new_frame.append(callee)
                stack.append(new_frame)
        else:
            itoposort[routine_key] = len(itoposort)

    toposort = [None] * len(itoposort)
    for symbol, index in itoposort.items():
        toposort[index] = symbol
    return toposort, itoposort

def allocate(files, exports, toposort):
    # {(filename, label): (callee_use_end, self_use_end), ...}
    func_allocation = {}
    for caller_key in toposort:
        filename, label = caller_key
        module = files[filename]
        caller_locals = module.locals_size.get(label, {})

        # find module for each callee
        callees = module.calls[label]
        tailcallees = module.tailcalls[label]
        callee_file = {}
        for callee in chain(callees, tailcallees):
            try:
                x = exports[callee]
            except KeyError:
                callee_file[callee] = filename
            else:
                callee_file[callee] = x[0]

        # Start caller's variables after the self_use_end of its callees
        # and after the callee_use_end of its tail callees
        callee_max = 0
        for callee in callees:
            callee_key = callee_file[callee], callee
            callee_uses = func_allocation[callee_key]
##            print("  callee %s in %s uses %d-%d <-"
##                  % (callee, callee_key[1], callee_uses[0], callee_uses[1]))
            callee_max = max(callee_uses[1], callee_max)
        for callee in tailcallees:
            callee_key = callee_file[callee], callee
            try:
                callee_uses = func_allocation[callee_key]
            except KeyError:
                print("warning: %s in %s tailcall loop to %s in %s"
                      % (callee_key[1], callee_key[0], label, filename),
                      file=sys.stderr)
                continue
##            print("  tail callee %s in %s uses -> %d-%d"
##                  % (callee, callee_key[1], callee_uses[0], callee_uses[1]))
            callee_max = max(callee_uses[0], callee_max)

        self_total = sum(caller_locals.values())
        func_allocation[caller_key] = callee_max, callee_max + self_total
    return func_allocation

def main(argv=None):
    args = parse_argv(argv or sys.argv)
    result = load_files(args.sourcefile, verbose=args.verbose)
    files, all_errors, all_warnings = result
    exports, errors = get_exports(files)
    all_errors.extend(errors)
    toposort, itoposort = postorder_callees(files, exports)
    print("All reachable routines, callees first:")
    print("\n".join(
        "%s::%s" % (os.path.splitext(os.path.basename(filename))[0], label)
        for filename, label in toposort
    ))
    allocation = allocate(files, exports, toposort)
    # TODO:
    # 1. figure out what to do with tail call loops
    # 2. write out allocation

    if all_errors:
        print("\n".join(
            "%s:%d: error: %s" % row for row in all_errors
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
