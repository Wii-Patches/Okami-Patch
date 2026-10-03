"""t_count.py image wait window addr... : plant counters on functions, report calls and last caller."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin
from hot import install_counters, read_counters
from dol import Dol
img, wait, window = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
addrs = [int(a, 16) for a in sys.argv[4:]]
dol = Dol(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'work', 'dols', 'ROWE08.dol'))
with Dolphin(img, gc=False, wiimote='nunchuk') as d:
    time.sleep(wait)
    slots = install_counters(d, dol, addrs)
    c0 = read_counters(d, slots); time.sleep(window); c1 = read_counters(d, slots)
    if os.environ.get('SHOT'):
        print('shot', d.screenshot(os.environ['SHOT']))
    for a in addrs:
        print('%08X  calls in window: %d  last caller LR %08X' % (a, c1[a][0] - c0[a][0], c1[a][1]))
