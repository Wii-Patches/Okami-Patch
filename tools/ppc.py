"""Small PowerPC analysis helpers on top of dol.Dol (capstone)."""
import struct, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from dol import Dol
from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN

_md = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)
_md.detail = False

def dis(dol, va, n=32, show=True):
    code = dol.read(va, n * 4)
    out = []
    for i in _md.disasm(code, va):
        out.append((i.address, i.mnemonic, i.op_str))
    if show:
        for a, m, o in out:
            print(f'{a:08X}  {dol.read(a,4).hex()}  {m} {o}')
    return out

def text_range(dol):
    return [(a, s) for o, a, s, i in dol.secs if i < 7]

def words(dol, va, n):
    return struct.unpack('>%dI' % n, dol.read(va, 4 * n))

def find_refs(dol, target, window=1):
    """Find lis/addi|ori|lwz|stw... pairs materialising `target` (r-relative or abs).
    Returns list of va of the low-half instruction."""
    hi = (target >> 16) & 0xFFFF
    lo = target & 0xFFFF
    hi_adj = (hi + (1 if lo & 0x8000 else 0)) & 0xFFFF
    res = []
    for a, s in text_range(dol):
        d = dol.read(a, s)
        regs = {}
        for off in range(0, s, 4):
            w = struct.unpack_from('>I', d, off)[0]
            op = w >> 26
            if op == 15:  # addis / lis
                rt = (w >> 21) & 31; ra = (w >> 16) & 31; imm = w & 0xFFFF
                if ra == 0: regs[rt] = (imm, a + off)
                else: regs.pop(rt, None)
            elif op in (14, 24, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 48, 49, 50, 51, 52, 53):
                ra = (w >> 16) & 31; imm = w & 0xFFFF
                if ra in regs and regs[ra][0] == hi_adj and imm == lo and (op != 24 or True):
                    if (op == 24 and hi == regs[ra][0]) or op != 24:
                        res.append(a + off)
                if op in (14, 24, 32, 34, 40, 42, 44) :
                    rt = (w >> 21) & 31
                    # loads/addi overwrite rt (ra stored for ori)
                    if op == 24: regs.pop((w >> 16) & 31, None)
                    else: regs.pop(rt, None)
            if op == 18 or op == 16:
                pass
    return res

def func_start(dol, va, limit=0x2000):
    """Walk back from va to the previous blr/function boundary (heuristic: stwu r1 prologue)."""
    a = va
    for _ in range(limit // 4):
        w = struct.unpack('>I', dol.read(a, 4))[0]
        if (w >> 16) == 0x9421:  # stwu r1,-X(r1)
            return a
        a -= 4
    return None
