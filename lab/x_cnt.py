"""x_cnt.py <variant> <wiimote> <wait> addr... : counters planted early; print total calls + last caller LR."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin
from hot import install_counters, read_counters
import mkimage
which = {'none': [], 'cc': ['cc'], 'gc': ['gc'], 'ccgc': ['cc', 'gc']}[sys.argv[1]]
img = mkimage.make('ROWE08', which)
mode, wait = sys.argv[2], int(sys.argv[3])
addrs = [int(a, 16) for a in sys.argv[4:]]
with Dolphin(img, gc=False, wiimote=mode) as d:
    time.sleep(float(os.environ.get("EARLY", "6")))
    slots = install_counters(d, None, addrs)
    time.sleep(wait)
    c = read_counters(d, slots)
    for a in addrs:
        print('%08X  calls: %d  last LR %08X' % (a, c[a][0], c[a][1]))
