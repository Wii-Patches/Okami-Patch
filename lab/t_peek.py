import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin
addr, n, wait = int(sys.argv[2], 16), int(sys.argv[3], 0), int(sys.argv[4])
with Dolphin(sys.argv[1], gc=False, wiimote='nunchuk') as d:
    time.sleep(wait)
    open(sys.argv[5], 'wb').write(d.peek(addr, n))
