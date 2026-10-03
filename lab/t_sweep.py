"""Plant counters on every stwu-prologue function in [lo,hi) and report the ones called during a window."""
import os, sys, time, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin
from hot import install_counters, read_counters
from dol import Dol
img, wait, window, lo, hi = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4], 16), int(sys.argv[5], 16)
dol = Dol(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'work', 'dols', 'ROWE08.dol'))
words = struct.unpack('>%dI' % ((hi - lo) // 4), dol.read(lo, hi - lo))
funcs = [lo + 4 * i for i, w in enumerate(words) if (w >> 16) == 0x9421 and (w & 0x8000)]
funcs = funcs[:120]
print(len(funcs), 'functions')
with Dolphin(img, gc=False, wiimote='nunchuk') as d:
    time.sleep(wait)
    slots = install_counters(d, dol, funcs)
    c0 = read_counters(d, slots); time.sleep(window); c1 = read_counters(d, slots)
    for a in funcs:
        n = c1[a][0] - c0[a][0]
        if n: print('%08X  %6d calls  last LR %08X' % (a, n, c1[a][1]))
