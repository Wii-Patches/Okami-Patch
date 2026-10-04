"""Boot with one generated Gecko code and show what the game's WPADStatus looks like for each input.

    x_pad.py <ignored> <none|cc|gc|ccgc> <wiimote: classic|nunchuk|none> <gc 0|1> <boot wait>
"""
import os, sys, time, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin
from hot import install_buf_probe
img, title, mode, gc, wait = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == '1', int(sys.argv[5])
import mkimage
which = {'none': [], 'cc': ['cc'], 'gc': ['gc'], 'ccgc': ['cc', 'gc']}[title]
REG = os.environ.get('REGION', 'ROWE08')
PROBE_AT, PROBE_REG = {'ROWE08': (0x80096664, 30), 'ROWP08': (0x80096790, 30), 'ROWJ08': (0x8009C978, 29)}[REG]
img = mkimage.make(REG, which)
with Dolphin(img, gc=gc, wiimote=mode, region=REG) as d:
    time.sleep(wait)
    slot = install_buf_probe(d, PROBE_AT, 0x80010024, reg=PROBE_REG, nwords=24)   # lwz r0,0x24(r1): r30 still the buffer
    def show(tag):
        time.sleep(1.0)
        b = d.peek(slot, 0x64)
        print('%-9s btn=%04X acc=%s dev=%d err=%d ext=%s obj0=%s hits=%d' % (tag, struct.unpack('>H', b[0:2])[0], struct.unpack('>3h', b[2:8]), b[0x28], b[0x29],
              b[0x2a:0x32].hex(' '), b[8:16].hex(' '), struct.unpack('>I', b[0x60:0x64])[0] if len(b) >= 0x64 else -1), flush=True)
    show('idle')
    pipe = d.gc if gc else d.wii
    for n in ('A', 'B', 'X', 'Y', 'START', 'L', 'R', 'D_UP', 'D_LEFT') + (('Z',) if gc else ()):
        pipe.press(n); show(n); pipe.release(n)
    pipe.axis('MAIN', 1.0, 0.5); show('Lstk R'); os.environ.get('SHOT') and print(d.screenshot(os.environ['SHOT'])); pipe.axis('MAIN', 0.5, 1.0); show('Lstk U'); pipe.axis('MAIN', 0.5, 0.5)
    pipe.axis('C', 1.0, 0.5); show('Rstk R'); pipe.axis('C', 0.5, 1.0); show('Rstk U'); pipe.axis('C', 0.0, 0.0); show('Rstk DL'); pipe.axis('C', 0.5, 0.5)
    show('idle2')
