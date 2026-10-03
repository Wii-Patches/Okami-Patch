"""Count calls to a set of function addresses over a window: t_trace.py image wait window addr..."""
import os, sys, time, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin
img, wait, window = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
addrs = [int(a, 16) for a in sys.argv[4:]]
with Dolphin(img, gc=False, wiimote='nunchuk') as d:
    time.sleep(wait)
    g = d.g
    g.interrupt()
    for a in addrs:
        g.cmd('Z0,%x,4' % a)
    cnt = collections.Counter(); lrs = collections.defaultdict(collections.Counter)
    g.send('c'); g.s.settimeout(1.0)
    t0 = time.time()
    while time.time() - t0 < window:
        try:
            r = g.recv()
        except Exception:
            continue
        if r.startswith('T') or r.startswith('S'):
            pc = int(g.cmd('p40'), 16); lr = int(g.cmd('p43'), 16)
            cnt[pc] += 1; lrs[pc][lr] += 1
            # step over the breakpoint: remove, single step, re-add
            g.cmd('z0,%x,4' % pc); g.send('s'); g.recv(); g.cmd('Z0,%x,4' % pc); g.send('c')
    g.interrupt()
    for a in addrs: g.cmd('z0,%x,4' % a)
    for pc, n in cnt.most_common():
        print('%08X x%d  callers %s' % (pc, n, [('%08X' % l, c) for l, c in lrs[pc].most_common(4)]))
    if not cnt: print('no hits')
