import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dolphin import Dolphin
snaps = []
with Dolphin(sys.argv[1], gc=False, wiimote='nunchuk') as d:
    for t in (40, 270):
        time.sleep(t - (0 if not snaps else 40))
        snaps.append(d.peek(0x80001800, 0x1900))
        open('/Users/larsen/okami-lab/low_%d.bin' % t, 'wb').write(snaps[-1])
for name, s in zip(('40s', '270s'), snaps):
    z = [i for i in range(0, len(s), 0x40) if not any(s[i:i + 0x40])]
    runs = []; 
    for i in z:
        if runs and runs[-1][1] == i: runs[-1][1] = i + 0x40
        else: runs.append([i, i + 0x40])
    print(name, ['%08X-%08X' % (0x80001800 + a, 0x80001800 + b) for a, b in runs])
