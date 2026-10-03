"""Dev-time assembler: turns src/*.s into the words shipped in tools/prebuilt/.

Needs devkitPPC (powerpc-eabi-as / -ld).  End users never run this -- the
patcher reads the prebuilt JSON, which gen_prebuilt.py regenerates and checks.
"""
import os
import shutil
import subprocess
import tempfile

DKP = os.environ.get('DEVKITPPC', '/opt/devkitpro/devkitPPC')


def _tool(name):
    p = os.path.join(DKP, 'bin', 'powerpc-eabi-' + name)
    if os.path.exists(p):
        return p
    return shutil.which('powerpc-eabi-' + name) or p


def assemble(source, base, syms=None, consts=None):
    """Assemble `source` (text) to bytes located at `base`.

    `syms` become link-time absolute symbols, so `bl helper` / `b RET` encode
    correctly relative to `base`.  `consts` are assemble-time numbers, usable in
    expressions such as `addi r3,r3,-DEAD`.
    """
    syms = syms or {}
    consts = consts or {}
    with tempfile.TemporaryDirectory() as t:
        s, o, bn = (os.path.join(t, n) for n in ('a.s', 'a.o', 'a.bin'))
        with open(s, 'w') as f:
            f.write('.globl _start\n_start:\n' + source + '\n')
        cmd_as = [_tool('as'), '-mbig', '-mgekko', s, '-o', o]
        for k, v in consts.items():
            cmd_as[1:1] = ['-defsym', '%s=%d' % (k, v)]
        subprocess.run(cmd_as, check=True)
        cmd = [_tool('ld'), '-Ttext=0x%X' % base, '--oformat', 'binary', o, '-o', bn]
        for k, v in syms.items():
            cmd[1:1] = ['--defsym', '%s=0x%X' % (k, v)]
        subprocess.run(cmd, check=True)
        return open(bn, 'rb').read()


def words(data):
    import struct
    return list(struct.unpack('>%dI' % (len(data) // 4), data))


CFLAGS = ['-O2', '-mcpu=750', '-msoft-float', '-msdata=none', '-ffreestanding', '-fno-pic', '-fno-builtin',
          '-fno-stack-protector', '-fno-jump-tables', '-fno-asynchronous-unwind-tables', '-fomit-frame-pointer',
          '-fno-ident', '-Wall', '-Werror']


def compile_hook(c_source, stub_source, base, defines=None, syms=None):
    """Build a C hook: `b stub`, the C code (entry `func`), then the asm `stub`.

    The first word jumps over the C code, so the whole blob can be run from its
    first byte (that is where a Hook's branch lands).  The stub must end just
    before the word the injector turns into the branch back.  Returns bytes.
    """
    defines = defines or {}
    syms = syms or {}
    with tempfile.TemporaryDirectory() as t:
        def p(n):
            return os.path.join(t, n)
        open(p('entry.s'), 'w').write('.globl _start\n_start:\n    b stub\n')
        open(p('stub.s'), 'w').write(stub_source)
        open(p('hook.c'), 'w').write(c_source)
        cc = [_tool('gcc'), '-c', p('hook.c'), '-o', p('hook.o')] + CFLAGS
        for k, v in defines.items():
            cc.append('-D%s=0x%XU' % (k, v))
        subprocess.run(cc, check=True)
        for n in ('entry', 'stub'):
            subprocess.run([_tool('as'), '-mbig', '-mgekko', p(n + '.s'), '-o', p(n + '.o')], check=True)
        ld = [_tool('ld'), '-Ttext=0x%X' % base, '--oformat', 'binary', p('entry.o'), p('hook.o'), p('stub.o'),
              '-o', p('out.bin')]
        for k, v in syms.items():
            ld[1:1] = ['--defsym', '%s=0x%X' % (k, v)]
        subprocess.run(ld, check=True)
        # a data or rodata section would land after the code and break the "one run of words" model
        sizes = subprocess.run([_tool('size'), '-A', p('hook.o')], capture_output=True, text=True).stdout
        extra = [l.split()[0] for l in sizes.splitlines() if l.startswith(('.rodata', '.data', '.sdata', '.bss', '.sbss', '.sdata2', '.rodata'))
                 and int(l.split()[1]) > 0]
        if extra:
            raise RuntimeError('hook.c needs data sections (%s): keep it free of globals and tables' % ', '.join(extra))
        return open(p('out.bin'), 'rb').read()
