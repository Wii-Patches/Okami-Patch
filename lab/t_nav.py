"""Tap buttons to get through intros, with a window screenshot every 30 s and the KPAD state."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin, LAB_DIR
img, mode, wait = sys.argv[1], sys.argv[2], int(sys.argv[3])
os.makedirs(LAB_DIR + '/shots', exist_ok=True)
with Dolphin(img, gc=False, wiimote=mode) as d:
    t0 = time.time(); n = 0
    while time.time() - t0 < wait:
        for b in ('A', 'START'):
            d.wii.tap(b, 0.2)
        time.sleep(2.5)
        k = d.kpad()
        if int(time.time() - t0) // 30 > n:
            n += 1; d.screenshot(LAB_DIR + '/shots/nav_%02d.png' % n)
            print(int(time.time() - t0), 'dev', k['dev'], 'hold', hex(k['hold']), 'shot', n, flush=True)
