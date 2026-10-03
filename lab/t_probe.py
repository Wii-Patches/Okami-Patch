import os, sys, time, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin
from hot import install_reg_probe
with Dolphin(sys.argv[1], gc=False, wiimote=sys.argv[3]) as d:
    time.sleep(int(sys.argv[2]))
    slot = install_reg_probe(d, 0x8042446C, 0x2C030000, regs=(3, 4))
    for i in range(4):
        time.sleep(3)
        v = struct.unpack('>4I', d.peek(slot, 16)); print('r3 (probe result) = %d, r4 = %08X, hits=%d' % (struct.unpack('>i', struct.pack('>I', v[0]))[0], v[1], v[2]))
