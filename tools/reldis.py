import sys,struct
sys.path.insert(0,__import__('os').path.dirname(__file__))
from rel import Rel
from capstone import *
md=Cs(CS_ARCH_PPC,CS_MODE_32|CS_MODE_BIG_ENDIAN)
def dis(r,sec,off,n,reloc=None):
    o,l,_=r.sections[sec]
    code=r.d[o+off:o+off+4*n]
    rl={}
    if reloc is not None:
        for m,s,ofs,t,ts,ad in reloc:
            if s==sec: rl[ofs]=(m,t,ts,ad)
    for i in md.disasm(code,off):
        extra=''
        if i.address in rl: extra='   ; reloc mod%d type%d sec%d +%#x'%rl[i.address]
        print(f'{i.address:07X}  {code[i.address-off:i.address-off+4].hex()}  {i.mnemonic} {i.op_str}{extra}')
