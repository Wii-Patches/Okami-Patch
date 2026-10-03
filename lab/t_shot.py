import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin, LAB_DIR
img, mode, wait = sys.argv[1], sys.argv[2], int(sys.argv[3])
os.makedirs(LAB_DIR + '/shots', exist_ok=True)
with Dolphin(img, gc=False, wiimote=mode) as d:
    time.sleep(wait)
    print('shot', d.screenshot(LAB_DIR + '/shots/win.png'))
