import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin
with Dolphin(sys.argv[1], gc=False, wiimote='nunchuk') as d:
    time.sleep(int(sys.argv[2]))
    g = d.g
    print('intr', g.interrupt())
    print('?', g.cmd('?'))
    print('pc', g.cmd('p40'), 'lr', g.cmd('p43'))
    print('Z0', g.cmd('Z0,800339a8,4'), 'Z1', g.cmd('Z1,800339a8,4'))
    g.send('c'); g.s.settimeout(5)
    try:
        print('stop:', g.recv())
        print('pc', g.cmd('p40'))
    except Exception as e:
        print('no stop', repr(e))
