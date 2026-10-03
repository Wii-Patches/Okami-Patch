"""Run Okami in a private Dolphin and read the game's KPAD state back over GDB.

A throwaway Dolphin user folder (config, saves, pipes) is built per run, so
every run starts from the same state.  Input goes in through Dolphin's Pipe
device (a named pipe per controller); the KPAD channel structs are read over
Dolphin's GDB stub, so no screen scraping is needed to know whether a press
arrived.  Patches can be hot-loaded into the running game with poke(), which
avoids rebuilding a 4 GB disc image for every change.

    from dolphin import Dolphin
    with Dolphin(image, gc=True, wiimote='nunchuk') as d:
        d.wait_boot()
        d.gc.press('A'); print(d.kpad(0))

Everything big (the private Dolphin copy, the user folder, images) lives in
LAB_DIR (default ~/okami-lab) because the repo's disk may be short of space.
"""
import os
import shutil
import signal
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gdbmem import Gdb

LAB_DIR = os.environ.get('LAB_DIR', os.path.expanduser('~/okami-lab'))
# A private, renamed copy of Dolphin.app: other projects' test scripts `pkill Dolphin`.
DOLPHIN = os.environ.get('DOLPHIN', os.path.join(LAB_DIR, 'okamiemu.app', 'Contents', 'MacOS', 'okamiemu'))
GDB_PORT = int(os.environ.get('LAB_GDB_PORT', 2271))

# KPAD channel 0 struct per region; stride 0x524 between channels
KPAD0 = {'ROWE08': 0x802126B8}
KPAD_STRIDE = 0x524

# Classic Controller input -> pipe input (what a test sends with wii.press / wii.axis)
CLASSIC = {
    'Buttons/A': 'Button A', 'Buttons/B': 'Button B', 'Buttons/X': 'Button X', 'Buttons/Y': 'Button Y',
    'Buttons/ZL': 'Button Z', 'Buttons/ZR': 'Button START', 'Buttons/+': 'Button L', 'Buttons/-': 'Button R',
    'Triggers/L': 'Axis L -+', 'Triggers/R': 'Axis R -+',
    'D-Pad/Up': 'Button D_UP', 'D-Pad/Down': 'Button D_DOWN', 'D-Pad/Left': 'Button D_LEFT', 'D-Pad/Right': 'Button D_RIGHT',
    'Left Stick/Up': 'Axis MAIN Y +', 'Left Stick/Down': 'Axis MAIN Y -', 'Left Stick/Left': 'Axis MAIN X -', 'Left Stick/Right': 'Axis MAIN X +',
    'Right Stick/Up': 'Axis C Y +', 'Right Stick/Down': 'Axis C Y -', 'Right Stick/Left': 'Axis C X -', 'Right Stick/Right': 'Axis C X +',
}
# plain Wii Remote (+ Nunchuk) inputs.  The pointer is driven by the C stick, the Nunchuk stick by MAIN.
REMOTE = {'Buttons/A': 'Button A', 'Buttons/B': 'Button B', 'Buttons/1': 'Button X', 'Buttons/2': 'Button Y',
          'Buttons/+': 'Button START', 'Buttons/-': 'Button L', 'Buttons/Home': 'Button R',
          'D-Pad/Up': 'Button D_UP', 'D-Pad/Down': 'Button D_DOWN', 'D-Pad/Left': 'Button D_LEFT', 'D-Pad/Right': 'Button D_RIGHT',
          'IR/Up': 'Axis C Y +', 'IR/Down': 'Axis C Y -', 'IR/Left': 'Axis C X -', 'IR/Right': 'Axis C X +'}
NUNCHUK = {'Nunchuk/Buttons/C': 'Button Z', 'Nunchuk/Buttons/Z': 'Axis R -+',
           'Nunchuk/Stick/Up': 'Axis MAIN Y +', 'Nunchuk/Stick/Down': 'Axis MAIN Y -',
           'Nunchuk/Stick/Left': 'Axis MAIN X -', 'Nunchuk/Stick/Right': 'Axis MAIN X +'}
# which pipe name presses which Classic button
CC_PIPE = {'A': 'A', 'B': 'B', 'X': 'X', 'Y': 'Y', 'ZL': 'Z', 'ZR': 'START', '+': 'L', '-': 'R',
           'Up': 'D_UP', 'Down': 'D_DOWN', 'Left': 'D_LEFT', 'Right': 'D_RIGHT'}

GC_NAMES = dict(A='A', B='B', X='X', Y='Y', Z='Z', Start='START', L='L', R='R',
                Up='D_UP', Down='D_DOWN', Left='D_LEFT', Right='D_RIGHT')


class Pipe:
    """One of Dolphin's named-pipe controllers: PRESS/RELEASE/SET lines."""

    def __init__(self, path):
        self.path = path
        self.f = None

    def open(self, timeout=60):
        end = time.time() + timeout
        while time.time() < end:
            try:
                self.f = os.open(self.path, os.O_WRONLY | os.O_NONBLOCK)
                return
            except OSError:
                time.sleep(0.5)
        raise TimeoutError('nobody opened ' + self.path)

    def cmd(self, s):
        os.write(self.f, (s + '\n').encode())

    def press(self, b):
        self.cmd('PRESS ' + b)

    def release(self, b):
        self.cmd('RELEASE ' + b)

    def axis(self, name, x, y):
        self.cmd('SET %s %.3f %.3f' % (name, x, y))

    def set1(self, name, v):
        self.cmd('SET %s %.3f' % (name, v))

    def tap(self, b, secs=0.25):
        self.press(b)
        time.sleep(secs)
        self.release(b)
        time.sleep(0.15)


def write_config(user, gc, wiimote, video_dump=False, gecko=None, game_id=None, sd=None):
    for d in ('Config', 'GameSettings', 'Pipes'):
        os.makedirs(os.path.join(user, d), exist_ok=True)
    pipes = os.path.join(user, 'Pipes')
    for n in ('gc', 'wii', 'hk'):
        p = os.path.join(pipes, n)
        if os.path.exists(p):
            os.unlink(p)
        os.mkfifo(p)
    open(os.path.join(user, 'Config', 'Dolphin.ini'), 'w').write(
        "[General]\nGDBPort = %d\n[Input]\nBackgroundInput = True\n[Interface]\nConfirmStop = False\nUsePanicHandlers = False\n"
        "[Core]\nMMU = True\nCPUThread = False\nCPUCore = 4\nEnableDebugging = True\nEnableCheats = True\n"
        "WiimoteContinuousScanning = False\nWiimoteControllerInterface = False\nEmulationSpeed = %s\n"
        "SIDevice0 = %d\nSIDevice1 = 0\nSIDevice2 = 0\nSIDevice3 = 0\n"
        "[DSP]\nBackend = No Audio Output\n"
        "[Analytics]\nPermissionAsked = True\nEnabled = False\n" % (GDB_PORT, os.environ.get("LAB_SPEED", "1.0"), 6 if gc else 0) +
        ("[Movie]\nDumpFrames = True\nDumpFramesSilent = True\nDumpFramesAsImages = True\n" if video_dump else ""))
    pad = "[GCPad1]\nDevice = Pipe/0/gc\n"
    pad += "".join("Buttons/%s = `Button %s`\n" % (b, b) for b in 'ABXYZ')
    pad += "Buttons/Start = `Button START`\n"
    pad += "".join("D-Pad/%s = `Button D_%s`\n" % (d.title(), d.upper()) for d in ('up', 'down', 'left', 'right'))
    pad += "Triggers/L = `Button L`\nTriggers/R = `Button R`\nTriggers/L-Analog = `Axis L -+`\nTriggers/R-Analog = `Axis R -+`\n"
    pad += "Main Stick/Up = `Axis MAIN Y +`\nMain Stick/Down = `Axis MAIN Y -`\nMain Stick/Left = `Axis MAIN X -`\nMain Stick/Right = `Axis MAIN X +`\n"
    pad += "C-Stick/Up = `Axis C Y +`\nC-Stick/Down = `Axis C Y -`\nC-Stick/Left = `Axis C X -`\nC-Stick/Right = `Axis C X +`\n"
    open(os.path.join(user, 'Config', 'GCPadNew.ini'), 'w').write(pad)
    # hotkeys on a third pipe: A = screenshot, B = save state slot 1, X = load state slot 1
    open(os.path.join(user, 'Config', 'Hotkeys.ini'), 'w').write(
        "[Hotkeys]\nDevice = Pipe/0/hk\nGeneral/Take Screenshot = `Button A`\n"
        "Save State/Save State Slot 1 = `Button B`\nLoad State/Load State Slot 1 = `Button X`\n")

    open(os.path.join(user, 'Config', 'Logger.ini'), 'w').write(
        '[Options]\nVerbosity = 5\nWriteToFile = True\nWriteToConsole = False\n[Logs]\nOSREPORT = True\nBOOT = True\nCORE = True\nPOWERPC = True\nWIIMOTE = True\nIOS_WIIMOTE = True\nIOS = True\nIOS_USB = True\n')
    if gecko:
        names = [l[1:].strip() for l in gecko.splitlines() if l.startswith('$')]
        open(os.path.join(user, 'GameSettings', game_id + '.ini'), 'w').write(
            '[Gecko]\n' + gecko.rstrip() + '\n[Gecko_Enabled]\n' + ''.join('$%s\n' % n for n in names))

    if wiimote:
        w = "[Wiimote1]\nSource = 1\nDevice = Pipe/0/wii\nExtension = %s\n" % {'classic': 'Classic', 'nunchuk': 'Nunchuk', 'none': 'None'}[wiimote]
        if wiimote in ('none', 'nunchuk'):
            for k, v in REMOTE.items():
                w += "%s = `%s`\n" % (k, v)
        if wiimote == 'nunchuk':
            for k, v in NUNCHUK.items():
                w += "%s = `%s`\n" % (k, v)
        if wiimote == 'classic':
            for k, v in CLASSIC.items():
                w += "Classic/%s = `%s`\n" % (k, v)
    else:
        w = "[Wiimote1]\nSource = 0\n"
    open(os.path.join(user, 'Config', 'WiimoteNew.ini'), 'w').write(w)


class Dolphin:
    def __init__(self, image, user=None, gc=False, wiimote=None, video=os.environ.get('LAB_VIDEO', 'Null'), region='ROWE08', video_dump=False,
                 gecko=None, keep_user=False, state=None):
        self.gecko = gecko
        self.image = os.path.abspath(image)
        self.user = os.path.abspath(user or os.environ.get('DOLPHIN_USER') or os.path.join(LAB_DIR, 'user'))
        self.gc_on, self.wii_on, self.video, self.region = gc, wiimote, video, region
        self.video_dump = video_dump
        self.keep_user = keep_user
        self.proc = None
        self.g = None
        self.gc = Pipe(os.path.join(self.user, 'Pipes', 'gc'))
        self.wii = Pipe(os.path.join(self.user, 'Pipes', 'wii'))
        self.hk = Pipe(os.path.join(self.user, 'Pipes', 'hk'))
        self.state = state

    def __enter__(self):
        if not self.keep_user:
            shutil.rmtree(self.user, ignore_errors=True)
        write_config(self.user, self.gc_on, self.wii_on, self.video_dump, self.gecko, self.region)
        cmd = [DOLPHIN, '-b', '-u', self.user, '-e', self.image, '-v', self.video] + (['-s', self.state] if self.state else [])
        self.proc = subprocess.Popen(cmd,
                                     stdout=open(os.path.join(LAB_DIR, 'dolphin_out.txt'), 'w'), stderr=subprocess.STDOUT)
        for _ in range(120):
            try:
                self.g = Gdb(port=GDB_PORT, timeout=30)
                break
            except OSError:
                time.sleep(1)
        else:
            raise RuntimeError('Dolphin GDB stub never came up')
        self.g.cont()
        if self.gc_on:
            self.gc.open()
        if self.wii_on:
            self.wii.open()
        self.hk.open()
        return self

    def __exit__(self, *a):
        try:
            if self.g:
                self.g.close()
        finally:
            if self.proc:
                self.proc.send_signal(signal.SIGTERM)
                try:
                    self.proc.wait(10)
                except subprocess.TimeoutExpired:
                    self.proc.kill()

    # -- memory -----------------------------------------------------------
    def peek(self, addr, n):
        self.g.interrupt()
        try:
            return self.g.read_mem(addr, n)
        finally:
            self.g.cont()

    def poke(self, addr, data):
        self.g.interrupt()
        try:
            self.g.cmd('M%x,%x:%s' % (addr, len(data), data.hex()))
        finally:
            self.g.cont()

    def kpad_base(self, chan=0):
        return KPAD0[self.region] + chan * KPAD_STRIDE

    def kpad(self, chan=0):
        b = self.peek(self.kpad_base(chan), 0x84)
        u32 = lambda o: struct.unpack('>I', b[o:o + 4])[0]
        f32 = lambda o: struct.unpack('>f', b[o:o + 4])[0]
        return dict(hold=u32(0), trig=u32(4), rel=u32(8), dev=b[0x5C], err=b[0x5D], dpd=b[0x5E], fmt=b[0x5F],
                    acc=(f32(0x0C), f32(0x10), f32(0x14)), ptr=(f32(0x20), f32(0x24)),
                    cl_hold=u32(0x60), fs_stick=(f32(0x60), f32(0x64)), ls=(f32(0x6C), f32(0x70)), rs=(f32(0x74), f32(0x78)))

    def screenshot(self, path):
        """Capture only the emulator's own window (never the whole screen)."""
        import Quartz
        best = None
        for w in Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID):
            if w.get('kCGWindowOwnerName') == 'okamiemu' and w['kCGWindowBounds']['Width'] > 300:
                if best is None or w['kCGWindowBounds']['Width'] > best['kCGWindowBounds']['Width']:
                    best = w
        if best is None:
            return False
        subprocess.run(['screencapture', '-x', '-o', '-l', str(best['kCGWindowNumber']), path], check=True)
        return True

    def save_state(self, dest, slot_wait=8):
        """Save state slot 1 through the hotkey pipe and copy it to `dest`."""
        self.hk.tap('B', 0.3)
        time.sleep(slot_wait)
        src = os.path.join(self.user, 'StateSaves', 'ROWE08.s01')
        for _ in range(30):
            cand = [f for f in os.listdir(os.path.join(self.user, 'StateSaves')) if f.endswith('.s01')] if os.path.isdir(os.path.join(self.user, 'StateSaves')) else []
            if cand:
                shutil.copyfile(os.path.join(self.user, 'StateSaves', cand[0]), dest)
                return dest
            time.sleep(1)
        raise RuntimeError('no state file appeared')

    def wait_boot(self, secs=25):
        time.sleep(secs)
