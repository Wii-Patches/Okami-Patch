"""Which data format does the game ask for, and what does the SDK settle on, for a given attached extension?"""
import os, sys, time, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin
from hot import install_reg_probe
img, mode, wait = sys.argv[1], sys.argv[2], int(sys.argv[3])
with Dolphin(img, gc=False, wiimote=mode) as d:
    time.sleep(8)
    slot = install_reg_probe(d, 0x80095DF4, 0x9421FFE0, regs=(3, 4))
    time.sleep(wait)
    b = d.peek(slot, 12)
    print('SetDataFormat last call: chan=%d fmt=%d hits=%d' % struct.unpack('>3I', b))
    p = struct.unpack('>I', d.peek(0x80213b90, 4))[0]
    c = d.peek(p + 0x8b0, 0x40)
    print('chan struct %08X: 0x8b8 fmt=%d  0x8c1 dev=%02X 0x8bc=%08X 0x8dc=%d' % (p, struct.unpack('>I', c[8:12])[0], c[0x11], struct.unpack('>I', c[12:16])[0], struct.unpack('>I', d.peek(p+0x8dc,4))[0]))
