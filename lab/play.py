"""Interactive driver: runs the game, taps through menus and takes window screenshots.

Control by writing one line into LAB_DIR/ctl:
    taps A,START      which buttons to tap every cycle (default A,START); 'none' stops tapping
    save NAME         save state slot 1 to LAB_DIR/states/NAME.sav
    hold NAME on|off  hold/release a Wii Remote pipe button (e.g. hold D_UP on)
    stick X Y         left (Nunchuk) stick, 0..1 with 0.5 centre
    shot NAME         screenshot to LAB_DIR/shots/NAME.png
    quit
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from dolphin import Dolphin, LAB_DIR
img = sys.argv[1]; mode = sys.argv[2] if len(sys.argv) > 2 else 'nunchuk'
state = sys.argv[3] if len(sys.argv) > 3 else None
ctl = LAB_DIR + '/ctl'
os.makedirs(LAB_DIR + '/shots', exist_ok=True); os.makedirs(LAB_DIR + '/states', exist_ok=True)
open(ctl, 'w').write('')
taps = ['A', 'START']
n = 0
with Dolphin(img, gc=False, wiimote=mode, state=state) as d:
    t0 = time.time()
    while True:
        for line in open(ctl).read().splitlines():
            p = line.split()
            if not p: continue
            if p[0] == 'quit': sys.exit(0)
            if p[0] == 'taps': taps = [] if p[1] == 'none' else p[1].split(',')
            if p[0] == 'save': print('saved', d.save_state(LAB_DIR + '/states/%s.sav' % p[1]), flush=True)
            if p[0] == 'hold': (d.wii.press if p[2] == 'on' else d.wii.release)(p[1])
            if p[0] == 'stick': d.wii.axis('MAIN', float(p[1]), float(p[2]))
            if p[0] == 'exec':
                try:
                    exec(open(p[1]).read())
                except Exception as e:
                    import traceback; traceback.print_exc()
                sys.stdout.flush()
            if p[0] == 'shot': print('shot', d.screenshot(LAB_DIR + '/shots/%s.png' % p[1]), flush=True)
        open(ctl, 'w').write('')
        for b in taps: d.wii.tap(b, 0.6)
        time.sleep(1.5)
        if time.time() - t0 > n * 20:
            d.screenshot(LAB_DIR + '/shots/live.png'); n += 1
