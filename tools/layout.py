"""Where the hook trampolines live in the injected low-memory section.

Every patch is a set of hooks: one instruction in the game is replaced by a
branch to a small self-contained routine that runs the displaced instruction
and branches back.  A Gecko code handler stores those routines itself (C2
codes); the patched DOL and the Riivolution patch need somewhere to put them,
so the patcher adds one text section at CAVE_BASE.

0x80001800-0x80003000 is the Wii's boot-time scratch area, which Okami itself
never executes from or stores to after boot (the retail DOLs reference 0x8000xxxx
only below 0x80001800 or from 0x80003000 up).  The first 0x20 bytes are skipped:
the word at 0x80001800 is overwritten by the OS early on.  The controller
routines hold no variables of their own.
"""
CAVE_BASE = 0x80001820
CAVE_LIMIT = 0x80003000

PAD_BASE = 0x80001820          # controller hook trampolines
PAD_END = 0x80003000

WINDOWS = {'cc': (PAD_BASE, PAD_END), 'gc': (PAD_BASE, PAD_END), 'ccgc': (PAD_BASE, PAD_END)}
