import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin, LAB_DIR
img, mode, wait = sys.argv[1], sys.argv[2], int(sys.argv[3])
with Dolphin(img, gc=False, wiimote=mode) as d:
    t0 = time.time()
    while time.time() - t0 < wait:
        time.sleep(6)
        d.wii.tap('A', 0.3); d.wii.tap('START', 0.3)
        k = d.kpad(); print(int(time.time() - t0), 'dev', k['dev'], 'err', k['err'], 'hold', hex(k['hold']), flush=True)
os.system("tail -4 %s/user/Logs/dolphin.log | cut -c1-160" % LAB_DIR)
