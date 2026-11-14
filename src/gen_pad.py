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
READ = (0x8009665C, 8, 4)        # WPADRead tail: `mr r3,r31`, r30 = WPADStatus handed to the game, r29 = the SDK's copy

# No Wii Remote (GameCube variants only):
NOREM = (0x80095C24, 12, 8)      # WPADProbe: `lwz r30,0x8bc(r31)` (r30 = type pointer); +0x30 = `bl OSRestoreInterrupts`
WAKE = (0x80090D74, 8, 8)        # KPADRead: `lbz r0,0x10f(r31)`, its sample count, right after WPADSetSamplingCallback
SAMPLER = (0x800916E4, 0, 10)    # KPAD's sampling callback (r3 = channel)

ORIG = dict(probe=0x901E0000, cb_new=0x7F63DB78, cb_rd=0x889F08C1, cb_cmd=0x889E08C1, read=0x7FE3FB78,
            norem=0x83DF08BC, wake=0x881F010F)
WAKE_CHAN = 27                   # KPADRead's channel register
WAKE_SAMPLES = 1                 # KPADRead goes on with one sample queued

# Japan carries a newer WPAD library: same logic, different code.  Sites are given outright, with the
# registers its compiler picked (the callback type is read through r28, WPADRead keeps the caller's
# buffer in r29, the SDK's copy in r31 and the interrupt state in r30).
# Its KPADRead probes first (and bails on -1), then wants more than one sample queued (`cmplwi r0,1; ble`).
JP = dict(sites=dict(probe=0x8009C004, cb_new=0x800A0478, cb_rd=0x800A1788, cb_cmd=0x800A1468, read=0x8009C970,
                     norem=0x8009C008, wake=0x800962D4, sampler=0x80097134),
          orig=dict(ORIG, cb_rd=0x889C08C1, cb_cmd=0x889E08C1, read=0x7FC3F378, wake=0x881A013B),
          wake_chan=25, wake_samples=2,
          cb_rd_reg=28, read_buf=29, read_src=31, read_displaced='mr 3,30')
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
# The data format is left at the Nunchuk format (5) the game asks for: the SDK still decodes a Classic
# Controller in it, but WPADRead hands the game only the first 0x32 bytes, which cuts off the right stick Y,
# so the read hook takes the Classic report from the SDK's own copy of the status.  (Switching the SDK to the
# Classic format (8), as earlier builds did, crashes the game in its stick-history code on all three
# releases as soon as the stick moves while the title screen's attract movie starts.)


# WPADProbe stand-in: ask fake_probe(r31, r30); when it answers 1, return 0 (connected).  r3 holds the
# OSDisableInterrupts level and must survive; everything else volatile is dead here.
NOREM_ASM = '''    stwu 1,-16(1)
    stw 3,8(1)
    mr 3,31
    mr 4,30
    bl fake_probe
    mr 0,3
    lwz 3,8(1)
    addi 1,1,16
    cmpwi 0,0
    lwz 30,0x8bc(31)
    beq 1f
    li 30,0
    b SKIP
1:
'''
# KPADRead: right after a call, so only non-volatile registers are live
WAKE_ASM = '''    mr 3,%d
    bl kpad_wake
    %s
'''


def _ha_lo(dol, lis_at, addi_at):
    hi = _word(dol, lis_at) & 0xFFFF
    lo = _word(dol, addi_at) & 0xFFFF
    return ((hi << 16) + (lo - 0x10000 if lo & 0x8000 else lo)) & 0xFFFFFFFF


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
    add('probe', PROBE, small(PROBE_ASM[variant]),
        'WPADProbe: the extension type the game sees is always Nunchuk')
    if mode & 1:
        add('cb_new', CB_NEW, small(CB_NEW_ASM), 'extension callback: a Classic Controller is announced as a Nunchuk')
        add('cb_rd', CB_RD, small(CB_RD_ASM % (jp['cb_rd_reg'] if jp else 31)), 'extension callback (polled path): same')
        if True:
            add('cb_cmd', CB_CMD, small(CB_RD_ASM % 30), 'extension callback (command-completion path): same')
    defines = dict({'MODE': mode}, **EXTRA_DEFINES)
    if mode & 2:
        norem = site('norem', NOREM)
        # the channel table is built by `lis r5` / `addi r5` at the top of WPADProbe
        defines['WPAD_CHANS'] = _ha_lo(dol, norem - 0x34, norem - 0x28)
        defines['KPAD_SAMPLER'] = site('sampler', SAMPLER)
        defines['KPAD_SAMPLES'] = jp['wake_samples'] if jp else WAKE_SAMPLES
        if jp:
            defines['ANNOUNCE_CONNECT'] = 1
        if _word(dol, defines['KPAD_SAMPLER']) >> 16 != 0x9421:
            raise SystemExit('%s: KPAD sampler 0x%08X is not a function start' % (region, defines['KPAD_SAMPLER']))
    blob, syms = asm.compile_hook(_read('pad.c'), _read('pad_stub.s').replace('@BUF@', str(jp['read_buf'] if jp else 30)).replace('@SRC@', str(jp['read_src'] if jp else 29)).replace('@DISPLACED@', '    ' + (jp['read_displaced'] if jp else 'mr 3,31')), cur,
                                  defines, symbols=True)
    add('read', READ, asm.words(blob), 'WPADRead tail: rewrite the status as a Wii Remote + Nunchuk (buttons, stick, IR pointer)')
    if mode & 2:
        add('norem', NOREM, asm.words(asm.assemble(NOREM_ASM, cur, dict(fake_probe=syms['fake_probe'], SKIP=norem + 0x30))),
            'WPADProbe: with no Wii Remote on channel 0 but a GameCube pad answering, report a remote + Nunchuk')
        wake_disp = 'lbz 0,0x13b(26)' if jp else 'lbz 0,0x10f(31)'
        add('wake', WAKE, asm.words(asm.assemble(WAKE_ASM % (jp['wake_chan'] if jp else WAKE_CHAN, wake_disp), cur,
                                                 dict(kpad_wake=syms['kpad_wake']))),
            'KPADRead: with no Wii Remote, take samples through KPAD so the GameCube pad reaches the game')
    if cur > PAD_END:
        raise SystemExit('pad code overflows its window: 0x%X > 0x%X' % (cur, PAD_END))
    return Feature(variant, TITLES[variant], region, ops)
