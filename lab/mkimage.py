#!/usr/bin/env python3
"""Build a patched test disc folder: patch a region's retail main.dol and drop it into the
extracted disc, which Dolphin boots straight from its sys/main.dol (no image rebuild).

    python3 lab/mkimage.py ROWE08 cc        ->  ~/okami-lab/disc_ROWE08/sys/main.dol  (prints its path)
    python3 lab/mkimage.py ROWE08           ->  retail main.dol restored
"""
import os
import shutil
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import patcher
from dol import Dol

LAB = os.environ.get('LAB_DIR', os.path.expanduser('~/okami-lab'))


def make(region, which=()):
    disc = os.path.join(LAB, 'disc_' + region)
    retail = os.path.join(ROOT, 'work', 'dols', region + '.dol')
    target = os.path.join(disc, 'sys', 'main.dol')
    if not which:
        shutil.copyfile(retail, target)
        return target
    d = Dol(retail)
    patcher.patch(d, region, which)
    d.save(target)
    return target


if __name__ == '__main__':
    print(make(sys.argv[1], sys.argv[2:]))
