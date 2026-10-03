import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin
with Dolphin(sys.argv[1], gc=False, wiimote='nunchuk') as d:
    time.sleep(int(sys.argv[2]))
    for i in range(8):
        d.g.interrupt()
        pc = d.g.cmd('p40'); lr = d.g.cmd('p43')
        print('pc', pc, 'lr', lr, flush=True)
        d.g.cont(); time.sleep(1.5)
