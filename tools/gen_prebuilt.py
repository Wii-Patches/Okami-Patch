#!/usr/bin/env python3
"""Regenerate tools/prebuilt/*.json from src/ (needs devkitPPC and the retail DOLs).

    OKAMI_DOLS=/path/with/ROWE08.dol,ROWP08.dol,ROWJ08.dol  python3 tools/gen_prebuilt.py [cc|gc|ccgc ...]

Each retail DOL can instead be given as OKAMI_DOL_<ID>.  The JSON is what the
patcher ships and reads; end users do not need devkitPPC or any game files here.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
from dol import Dol
from features import PREBUILT, dump
from regions import REGIONS


def dol_for(region):
    env = os.environ.get('OKAMI_DOL_' + region)
    if env:
        return Dol(env)
    base = os.environ.get('OKAMI_DOLS')
    if base:
        p = os.path.join(base, region + '.dol')
        if os.path.exists(p):
            return Dol(p)
    sys.exit('set OKAMI_DOLS=<dir with %s.dol> or OKAMI_DOL_%s=<path>' % (region, region))


def main(argv):
    which = argv or ['cc', 'gc', 'ccgc']
    os.makedirs(PREBUILT, exist_ok=True)
    for name in which:
        mod = __import__('gen_pad')
        mod.USA_DOL = dol_for('ROWE08')
        for region in REGIONS:
            try:
                f = mod.build(name, region, dol_for(region))
            except NotImplementedError as e:
                print('%-4s %s  skipped: %s' % (name, region, e))
                continue
            path = os.path.join(PREBUILT, '%s_%s.json' % (name, region))
            with open(path, 'w') as fh:
                json.dump(dump(f), fh, indent=1)
                fh.write('\n')
            print('%-3s %s  %d ops -> %s' % (name, region, len(f.ops), os.path.relpath(path)))


if __name__ == '__main__':
    main(sys.argv[1:])
