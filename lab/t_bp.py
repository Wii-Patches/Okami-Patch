import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin
addr = int(sys.argv[3], 16)
with Dolphin(sys.argv[1], gc=False, wiimote='nunchuk') as d:
    time.sleep(int(sys.argv[2]))
    d.g.interrupt()
    print(d.g.cmd('Z0,%x,4' % addr))
    d.g.send('c')
    d.g.s.settimeout(20)
    try:
        r = d.g.recv(); print('hit', r[:60]); 
        print('r3', d.g.cmd('p3'), 'r4', d.g.cmd('p4'), 'r5', d.g.cmd('p5'), 'lr', d.g.cmd('p43'))
    except Exception as e:
        print('no hit', e)
    d.g.cmd('z0,%x,4' % addr)
