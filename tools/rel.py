"""Nintendo REL module reader: sections and relocations (enough to see what a module calls in the DOL)."""
import struct

R_NAMES = {0: 'NONE', 1: 'ADDR32', 2: 'ADDR24', 3: 'ADDR16', 4: 'ADDR16_LO', 5: 'ADDR16_HI', 6: 'ADDR16_HA',
           7: 'ADDR14', 8: 'ADDR14_BRT', 9: 'ADDR14_BRNT', 10: 'REL24', 11: 'REL14',
           201: 'NOP', 202: 'SECTION', 203: 'END', 204: 'MRKREF'}


class Rel:
    def __init__(self, path):
        self.path = path
        self.d = open(path, 'rb').read()
        d = self.d
        (self.id, self.next, self.prev, self.nsec, self.sec_off, self.name_off, self.name_size, self.version,
         self.bss_size, self.rel_off, self.imp_off, self.imp_size) = struct.unpack('>12I', d[:0x30])
        (self.prolog_sec, self.epilog_sec, self.unres_sec, self.bss_sec) = d[0x30:0x34]
        self.prolog, self.epilog, self.unres = struct.unpack('>3I', d[0x34:0x40])
        self.sections = []
        for i in range(self.nsec):
            off, ln = struct.unpack('>2I', d[self.sec_off + 8 * i: self.sec_off + 8 * i + 8])
            self.sections.append((off & ~1, ln, bool(off & 1)))

    def relocs(self):
        """Yield (module, section, offset, type, target_section, addend) for every relocation."""
        d = self.d
        for k in range(self.imp_size // 8):
            mod, roff = struct.unpack('>2I', d[self.imp_off + 8 * k: self.imp_off + 8 * k + 8])
            p = roff
            sec = 0
            off = 0
            while True:
                delta, typ, tsec, addend = struct.unpack('>HBBI', d[p:p + 8])
                p += 8
                if typ == 203:
                    break
                if typ == 202:
                    sec = tsec
                    off = 0
                    continue
                off += delta
                if typ < 200:
                    yield mod, sec, off, typ, tsec, addend

    def sec_bytes(self, i):
        o, l, _x = self.sections[i]
        return self.d[o:o + l] if o else b''
