import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin
import mkimage
REG=sys.argv[1]; img = mkimage.make(REG, sys.argv[2].split(',') if sys.argv[2] != 'none' else [])
with Dolphin(img, gc=False, wiimote=sys.argv[3], region=REG) as d:
    time.sleep(85)
    d.wii.axis('MAIN', *[float(x) for x in os.environ.get('ST','1.0,0.5').split(',')]); time.sleep(8)
    for i in range(6):
        d.g.interrupt()
        print('pc', d.g.cmd('p40'), 'lr', d.g.cmd('p43'), flush=True)
        d.g.cont(); time.sleep(1.0)
