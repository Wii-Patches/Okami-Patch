"""Dump the full WPADStatus buffer (nunchuk+IR) for several pointer / stick / button states."""
import os, sys, time, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin
from hot import install_buf_probe
img, mode, wait = sys.argv[1], sys.argv[2], int(sys.argv[3])
with Dolphin(img, gc=False, wiimote=mode) as d:
    time.sleep(wait)
    slot = install_buf_probe(d, 0x8009665C, 0x7FE3FB78, reg=30, nwords=24)
    def show(tag):
        time.sleep(1.0)
        b = d.peek(slot, 0x60)
        print('%-9s btn=%04X acc=%s' % (tag, struct.unpack('>H', b[0:2])[0], struct.unpack('>3h', b[2:8])))
        print('   obj', b[8:0x28].hex(' ', 4), '| dev', b[0x28], 'err', b[0x29], '| ext', b[0x2a:0x32].hex(' '), '| rest', b[0x32:0x5c].hex(' ', 4), flush=True)
    show('idle')
    d.wii.axis('C', 0.5, 1.0); show('ptr up')
    d.wii.axis('C', 0.5, 0.0); show('ptr down')
    d.wii.axis('C', 0.0, 0.5); show('ptr left')
    d.wii.axis('C', 1.0, 0.5); show('ptr right')
    d.wii.axis('C', 0.5, 0.5)
    d.wii.axis('MAIN', 1.0, 0.5); show('stk right')
    d.wii.axis('MAIN', 0.5, 1.0); show('stk up')
    d.wii.axis('MAIN', 0.5, 0.5)
    d.wii.press('Z'); show('C btn'); d.wii.release('Z')
    d.wii.cmd('SET R 1.0'); show('Z btn'); d.wii.cmd('SET R 0.0')
    for n in ('A', 'B', 'X', 'Y', 'START', 'L', 'R', 'D_UP', 'D_LEFT'):
        d.wii.press(n); show(n); d.wii.release(n)
