"""Boot the stock/patched USA image with a given controller and print KPAD state."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin
img = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else 'nunchuk'
wait = int(sys.argv[3]) if len(sys.argv) > 3 else 40
with Dolphin(img, gc=False, wiimote=mode) as d:
    d.wait_boot(wait)
    for i in range(3):
        print('kpad', d.kpad()); time.sleep(1)
    d.wii.press('A'); time.sleep(1); print('A held', d.kpad()); d.wii.release('A')
    d.wii.axis('MAIN', 1.0, 0.5); time.sleep(1); print('stick right', d.kpad()); d.wii.axis('MAIN', 0.5, 0.5)
