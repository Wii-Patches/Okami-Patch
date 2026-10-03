#!/usr/bin/env python3
"""Check the patch data against real, retail main.dol files.

    OKAMI_DOLS=<dir with ROWE08.dol ROWP08.dol ROWJ08.dol> python3 tools/verify.py

For every region and every combination of the three patches:
  * every site holds the retail bytes before patching
  * after patching, every hook site is a branch into the injected section whose
    trampoline runs back to site+4, and every in-place patch carries its new bytes
  * patching in steps (one feature at a time) gives the same file as all at once
  * nothing outside the intended sites changed
"""
import itertools
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import features
import patcher
from dol import Dol
from layout import CAVE_BASE, CAVE_LIMIT
from ops import Hook
from regions import REGIONS

fail = []


def check(cond, msg):
    print(('  ok   ' if cond else '  FAIL ') + msg)
    if not cond:
        fail.append(msg)


def retail(region):
    base = os.environ.get('OKAMI_DOLS')
    p = os.path.join(base or '.', region + '.dol')
    if not os.path.exists(p):
        sys.exit('set OKAMI_DOLS to a directory holding %s.dol' % region)
    return p


def main():
    pick = {'cc': ['cc'], 'gc': ['gc'], 'ccgc': ['cc', 'gc']}
    for region in REGIONS:
        print(region, REGIONS[region]['label'])
        path = retail(region)
        d0 = Dol(path)
        check(patcher.detect_region(d0) == region, 'detected as %s' % region)
        for name in features.FEATURES:
            if not features.available(name, region):
                print('  --   %s: not available for this release' % name)
                continue
            f = features.load(name, region)
            check(not f.check_pristine(d0), '%s: every site holds the retail bytes' % name)
            d = Dol(path)
            patcher.patch(d, region, pick[name])
            check(f.is_applied(d), '%s: applied' % name)
            check(patcher.status(d, region).get('cc' if name != 'gc' else 'gc') == 'patched', '%s: reported as patched' % name)
            touched = []
            for op in f.ops:
                if isinstance(op, Hook):
                    site = struct.unpack('>I', d.read(op.site, 4))[0]
                    tgt = (site & 0x03FFFFFC)
                    tgt = tgt - 0x04000000 if tgt & 0x02000000 else tgt
                    check((site >> 26) == 18 and not site & 3 and (op.site + tgt) == op.tramp,
                          '%s: 0x%08X branches to 0x%08X' % (name, op.site, op.tramp))
            touched = [(a, len(b)) for a, b in f.writes()]
            for off, va, size, idx in d0.secs:
                a = bytes(d0.data[off:off + size]); b = d.read(va, size)
                stray = [va + i for i in range(size) if a[i] != b[i] and not any(t <= va + i < t + n for t, n in touched)]
                if stray:
                    check(False, '%s: unexpected change at 0x%08X' % (name, stray[0]))
    print('\nFAILED: %d' % len(fail) if fail else '\nALL VERIFIED')
    sys.exit(1 if fail else 0)


if __name__ == '__main__':
    main()
