import os, sys, time, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin
from hot import install_buf_probe
import mkimage
REG='ROWJ08'; img = mkimage.make(REG, ['cc'])
with Dolphin(img, gc=False, wiimote='classic', region=REG) as d:
    time.sleep(80)
    slot = install_buf_probe(d, 0x8009C978, 0x80010024, reg=29, nwords=24)
    for i in range(14):
        time.sleep(3)
        b = d.peek(slot, 0x64)
        print(i, struct.unpack('>I', b[0x60:0x64])[0], b[0x28], d.g.cmd('?')[:20] if False else '', flush=True)
        if i == 99: d.wii.axis('MAIN', 1.0, 0.5)
