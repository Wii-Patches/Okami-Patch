"""Show the WPADStatus buffer the game gets from WPADRead while a remote button is held."""
import os, sys, time, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin
from hot import install_buf_probe
img, mode, wait = sys.argv[1], sys.argv[2], int(sys.argv[3])
with Dolphin(img, gc=False, wiimote=mode, state=(sys.argv[4] if len(sys.argv) > 4 else None)) as d:
    time.sleep(wait)
    slot = install_buf_probe(d, 0x8009665C, 0x7FE3FB78, reg=30, nwords=14)   # mr r3,r31
    def show(tag):
        b = d.peek(slot, 60)
        print('%-10s btn=%04X acc=%s dev=%d err=%d ext=%s hits=%d' % (tag, struct.unpack('>H', b[0:2])[0], struct.unpack('>3h', b[2:8]), b[0x28], struct.unpack('>b', b[0x29:0x2a])[0], b[0x2a:0x36].hex(), struct.unpack('>I', b[56:60])[0]))
    show('idle')
    for name in ('A', 'B', 'X', 'Y', 'START', 'L', 'R', 'D_UP'):
        d.wii.press(name); time.sleep(1.2); show('press ' + name); d.wii.release(name); time.sleep(0.5)
    d.wii.axis('MAIN', 1.0, 0.5); time.sleep(1.2); show('stick R'); d.wii.axis('MAIN', 0.5, 0.5)
    d.wii.axis('MAIN', 0.5, 1.0); time.sleep(1.2); show('stick U'); d.wii.axis('MAIN', 0.5, 0.5)
    d.wii.press('Z'); time.sleep(1.2); show('C btn?'); d.wii.release('Z')
