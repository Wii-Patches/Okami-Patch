"""Peek the SDK's channel struct (format, device, the two status buffers) with a patch variant and extension."""
import os, sys, time, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin
import mkimage
which = {'none': [], 'cc': ['cc'], 'gc': ['gc'], 'ccgc': ['cc', 'gc']}[sys.argv[1]]
img = mkimage.make('ROWE08', which)
mode, wait = sys.argv[2], int(sys.argv[3])
with Dolphin(img, gc=False, wiimote=mode) as d:
    time.sleep(wait)
    if len(sys.argv) > 4:
        for n in sys.argv[4].split(','): d.wii.press(n)
    time.sleep(2)
    p = struct.unpack('>I', d.peek(0x80213b90, 4))[0]
    c = d.peek(p, 0x9e0)
    u32 = lambda o: struct.unpack('>I', c[o:o + 4])[0]
    print('chan %08X fmt(0x8b8)=%d dev(0x8c1)=%02X 0x8c8=%d 0x8bc=%08X 0x8dc=%d' % (p, u32(0x8b8), c[0x8c1], c[0x8c8], u32(0x8bc), u32(0x8dc)))
    for i in (0, 1):
        o = 0xa0 + 0x60 * i
        print('buf%d @+%X btn=%04X ext(0x2a)=%s  dev=%d err=%d' % (i, o, struct.unpack('>H', c[o:o+2])[0], c[o+0x2a:o+0x3a].hex(' '), c[o+0x28], c[o+0x29]))
