"""Boot an image with a controller attached, print the KPAD channel state every 15 s and keep the video frames."""
import os, sys, time, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin, LAB_DIR
img = sys.argv[1]; mode = sys.argv[2]; wait = int(sys.argv[3])
with Dolphin(img, gc=False, wiimote=mode, video='Null') as d:
    for t in range(0, wait, 15):
        time.sleep(15); k = d.kpad(); print(t + 15, 'dev', k['dev'], 'err', k['err'], 'hold', hex(k['hold']), flush=True)
    d.wii.press('A'); time.sleep(1); print('A', hex(d.kpad()['hold'])); d.wii.release('A')
fr = sorted(glob.glob(os.path.join(LAB_DIR, 'user', 'Dump', 'Frames', '**', '*.png'), recursive=True))
print(len(fr), fr[-1:])
