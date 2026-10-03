import os, sys, time, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin, KPAD0, KPAD_STRIDE
img, mode, wait = sys.argv[1], sys.argv[2], int(sys.argv[3])
with Dolphin(img, gc=False, wiimote=mode) as d:
    time.sleep(wait)
    d.wii.press('A')
    for i in range(3):
        for ch in range(4):
            b = d.peek(KPAD0['ROWE08'] + ch * KPAD_STRIDE, 0x524)
            print('ch', ch, 'dev', b[0x5c], 'err', b[0x5d], 'wr', b[0x10e], 'cnt', b[0x10f], 'busy', b[0x51c], hex(struct.unpack('>I', b[0:4])[0]))
        time.sleep(1)
    b = d.peek(KPAD0['ROWE08'], 0x524)
    print(b[:0x90].hex()); print(b[0x100:0x1a0].hex())
