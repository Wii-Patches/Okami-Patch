import os, sys, time, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin
with Dolphin(sys.argv[1], gc=True, wiimote=None) as d:
    time.sleep(int(sys.argv[2]))
    print('idle', d.peek(0xCD006404, 8).hex(), d.peek(0xCC006404, 8).hex())
    d.gc.press('A'); time.sleep(1); print('A   ', d.peek(0xCD006404, 8).hex())
    d.gc.release('A'); d.gc.axis('MAIN', 1.0, 0.5); time.sleep(1); print('stkR', d.peek(0xCD006404, 8).hex())
