"""Build the controller features for one region from src/pad.c + src/pad_stub.s.

Three variants share the same hook sites (so they cannot be combined with each
other, which is why "both" is its own feature):

    cc    Classic Controller          pad.c MODE=1
    gc    GameCube controller         pad.c MODE=2
    ccgc  both                        pad.c MODE=3
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import asm
from layout import PAD_BASE, PAD_END
from ops import Feature, Hook
from sig import find_unique

# USA addresses; the other releases are found by signature search.  (site, words before, words after)
PROBE = (0x80095C20, 8, 8)       # WPADProbe: `stw r0,0(r30)` stores the extension type for the caller
CB_NEW = (0x8009A0A8, 8, 6)      # WPAD ext-change: `mr r3,r27` right before the callback is called (r4 = type)
CB_RD = (0x8009AD28, 8, 6)       # WPAD ext-poll:   `lbz r4,0x8c1(r31)` right before the callback is called
CB_CMD = (0x8009ABE4, 8, 6)      # WPAD command done: `lbz r4,0x8c1(r30)` right before the callback is called
SETFMT = (0x80095E20, 8, 8)      # WPADSetDataFormat: `lwz r29,0x8dc(r31)`, r27 = requested format
READ = (0x8009665C, 8, 4)        # WPADRead tail: `mr r3,r31`, r30 = WPADStatus handed to the game

ORIG = dict(probe=0x901E0000, cb_new=0x7F63DB78, cb_rd=0x889F08C1, cb_cmd=0x889E08C1, setfmt=0x83BF08DC, read=0x7FE3FB78)

# Japan carries a newer WPAD library: same logic, different code.  Sites are given outright, with the
# registers its compiler picked (the callback type is read through r28, WPADRead keeps the caller's
# buffer in r29 and the interrupt state in r30).
JP = dict(sites=dict(probe=0x8009C004, cb_new=0x800A0478, cb_rd=0x800A1788, cb_cmd=0x800A1468, setfmt=0x8009C234, read=0x8009C970),
          orig=dict(ORIG, cb_rd=0x889C08C1, cb_cmd=0x889E08C1, read=0x7FC3F378),
          cb_rd_reg=28, read_buf=29, read_displaced='mr 3,30')
USA_DOL = None
EXTRA_DEFINES = {}               # lab builds: {'DEBUG_COUNTERS': 0x80002FF0}

MODES = {'cc': 1, 'gc': 2, 'ccgc': 3}
TITLES = {'cc': 'Classic Controller', 'gc': 'GameCube controller', 'ccgc': 'Classic and GameCube controllers'}

# Small hand-written trampolines.  Each ends with the word the injector turns into
# the branch back; the displaced instruction is repeated inside.
PROBE_ASM = {
    # report a Classic Controller (2) as a Nunchuk (1)
    'cc': '    cmplwi 0,2\n    bne 1f\n    li 0,1\n1:  stw 0,0(30)\n',
    # report "no extension" (0) as a Nunchuk: the GameCube pad stands in for it
    'gc': '    cmplwi 0,0\n    bne 1f\n    li 0,1\n1:  stw 0,0(30)\n',
    'ccgc': '    cmplwi 0,3\n    bge 1f\n    li 0,1\n1:  stw 0,0(30)\n',
}
CB_NEW_ASM = '    mr 3,27\n    cmplwi 4,2\n    bne 1f\n    li 4,1\n1:\n'
CB_RD_ASM = '    lbz 4,0x8c1(%d)\n    cmplwi 4,2\n    bne 1f\n    li 4,1\n1:\n'
# the game believes it has a Nunchuk and asks for format 5 (buttons+accel+IR+Nunchuk): give a real
# Classic Controller the matching Classic format (8) so the SDK decodes it properly
SETFMT_ASM = ('    lwz 29,0x8dc(31)\n    lbz 0,0x8c1(31)\n    cmpwi 0,2\n    bne 1f\n'
              '    cmpwi 27,5\n    bne 1f\n    li 27,8\n1:\n')


def _read(name):
    return open(os.path.join(HERE, name)).read()


def _word(dol, a):
    return struct.unpack('>I', dol.read(a, 4))[0]


def build(variant, region, dol):
    usa = dol if region == 'ROWE08' else USA_DOL
    jp = JP if region == 'ROWJ08' else None
    orig = jp['orig'] if jp else ORIG
    ops, cur = [], PAD_BASE

    def site(name, sig):
        if jp:
            return jp['sites'][name]
        return sig[0] if region == 'ROWE08' else find_unique(usa, dol, *sig)

    def add(name, sig, payload, note):
        nonlocal cur
        s = site(name, sig)
        if _word(dol, s) != orig[name]:
            raise SystemExit('%s: %s site 0x%08X is 0x%08X, expected 0x%08X' % (region, name, s, _word(dol, s), orig[name]))
        words = list(payload) + [0]
        ops.append(Hook(s, orig[name], words, cur, note=note))
        cur += (len(words) * 4 + 15) & ~15

    def small(src):
        return asm.words(asm.assemble(src, cur))

    mode = MODES[variant]
    if jp and mode & 1:
        # buttons work on the Japanese release, but the game stops polling WPADRead as soon as the
        # stick moves (seen in Dolphin); until that is understood the Classic Controller is USA/EU only
        raise NotImplementedError('Classic Controller support for the Japanese release is not working yet')
    add('probe', PROBE, small(PROBE_ASM[variant]),
        'WPADProbe: the extension type the game sees is always Nunchuk')
    if mode & 1:
        add('cb_new', CB_NEW, small(CB_NEW_ASM), 'extension callback: a Classic Controller is announced as a Nunchuk')
        add('cb_rd', CB_RD, small(CB_RD_ASM % (jp['cb_rd_reg'] if jp else 31)), 'extension callback (polled path): same')
        if True:
            add('cb_cmd', CB_CMD, small(CB_RD_ASM % 30), 'extension callback (command-completion path): same')
        add('setfmt', SETFMT, small(SETFMT_ASM), 'WPADSetDataFormat: Classic Controllers get the Classic data format')
    blob = asm.words(asm.compile_hook(_read('pad.c'), _read('pad_stub.s').replace('@BUF@', str(jp['read_buf'] if jp else 30)).replace('@DISPLACED@', '    ' + (jp['read_displaced'] if jp else 'mr 3,31')), cur,
                                      dict({'MODE': mode}, **EXTRA_DEFINES))) + [0]
    add('read', READ, blob[:-1], 'WPADRead tail: rewrite the status as a Wii Remote + Nunchuk (buttons, stick, IR pointer)')
    if cur > PAD_END:
        raise SystemExit('pad code overflows its window: 0x%X > 0x%X' % (cur, PAD_END))
    return Feature(variant, TITLES[variant], region, ops)
