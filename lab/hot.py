"""Hot-patching helpers: PPC encoders and call counters planted into a running game over GDB.

A counter replaces a function's first instruction with a branch to a small stub in low memory
(0x80002400..) that counts calls, remembers the caller's LR, runs the displaced instruction and
branches back.  The first instruction must not be PC-relative (stwu/mflr/etc. are fine).
"""
import os, struct, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))

STUBS = 0x80002400     # above the patch cave, which ends before 0x80002400
SLOTS = 0x80002A00


def lis(r, v): return 0x3C000000 | (r << 21) | (v & 0xFFFF)
def addi(rt, ra, v): return 0x38000000 | (rt << 21) | (ra << 16) | (v & 0xFFFF)
def lwz(rt, off, ra): return 0x80000000 | (rt << 21) | (ra << 16) | (off & 0xFFFF)
def stw(rs, off, ra): return 0x90000000 | (rs << 21) | (ra << 16) | (off & 0xFFFF)
def mflr(r): return 0x7C0802A6 | (r << 21)
def b(src, dst): return 0x48000000 | ((dst - src) & 0x03FFFFFC)


def install_counters(d, dol, funcs):
    """funcs: list of addresses.  Returns {addr: slot}."""
    out = {}
    d.g.interrupt()
    try:
        for i, f in enumerate(funcs):
            slot = SLOTS + 16 * i
            stub = STUBS + 0x30 * i
            raw = dol.read(f, 4) if dol is not None else None
            orig = struct.unpack('>I', raw if raw is not None else d.g.read_mem(f, 4))[0]
            code = [lis(12, 0x8000), lwz(11, slot - 0x80000000, 12), addi(11, 11, 1), stw(11, slot - 0x80000000, 12),
                    mflr(11), stw(11, slot - 0x80000000 + 4, 12), orig, 0]
            code[-1] = b(stub + 4 * 7, f + 4)
            blob = struct.pack('>%dI' % len(code), *code)
            d.g.cmd('M%x,%x:%s' % (stub, len(blob), blob.hex()))
            d.g.cmd('M%x,%x:%s' % (slot, 16, '00' * 16))
            d.g.cmd('M%x,4:%08x' % (f, b(f, stub)))
            out[f] = slot
    finally:
        d.g.cont()
    return out


def read_counters(d, slots):
    d.g.interrupt()
    try:
        return {f: struct.unpack('>II', d.g.read_mem(s, 8)) for f, s in slots.items()}
    finally:
        d.g.cont()


def stw_r(rs, off, ra): return stw(rs, off, ra)


def install_reg_probe(d, addr, orig, regs=(3, 4), slot=SLOTS + 0x100, stub=STUBS + 0x200):
    """At `addr` (holding the non-PC-relative instruction `orig`), store the listed registers
    into `slot`, +4, ... and a hit counter after them, then run `orig` and carry on."""
    code = [lis(12, 0x8000)]
    for i, r in enumerate(regs):
        code.append(stw(r, slot - 0x80000000 + 4 * i, 12))
    n = slot - 0x80000000 + 4 * len(regs)
    code += [stw(11, n + 8, 12), lwz(11, n, 12), addi(11, 11, 1), stw(11, n, 12)]
    # (r11 restored below is not needed: callers treat r11 as scratch at this point)
    code += [orig, 0]
    code[-1] = b(stub + 4 * (len(code) - 1), addr + 4)
    blob = struct.pack('>%dI' % len(code), *code)
    d.g.interrupt()
    try:
        d.g.cmd('M%x,%x:%s' % (stub, len(blob), blob.hex()))
        d.g.cmd('M%x,10:%s' % (slot, '00' * 16))
        d.g.cmd('M%x,4:%08x' % (addr, b(addr, stub)))
    finally:
        d.g.cont()
    return slot


def install_buf_probe(d, addr, orig, reg=30, nwords=14, slot=SLOTS + 0x200, stub=STUBS + 0x300):
    """At `addr`, copy `nwords` words from the buffer pointed to by `reg` into `slot` (+ hit counter after),
    then run `orig` and carry on.  Uses r11/r12 as scratch, so `addr` must be a point where they are dead."""
    code = [lis(12, 0x8000)]
    for i in range(nwords):
        code += [lwz(11, 4 * i, reg), stw(11, slot - 0x80000000 + 4 * i, 12)]
    n = slot - 0x80000000 + 4 * nwords
    code += [lwz(11, n, 12), addi(11, 11, 1), stw(11, n, 12), orig, 0]
    code[-1] = b(stub + 4 * (len(code) - 1), addr + 4)
    blob = struct.pack('>%dI' % len(code), *code)
    d.g.interrupt()
    try:
        d.g.cmd('M%x,%x:%s' % (stub, len(blob), blob.hex()))
        d.g.cmd('M%x,%x:%s' % (slot, 4 * nwords + 4, '00' * (4 * nwords + 4)))
        d.g.cmd('M%x,4:%08x' % (addr, b(addr, stub)))
    finally:
        d.g.cont()
    return slot
