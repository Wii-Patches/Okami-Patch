#!/usr/bin/env python3
"""Emit the Gecko code lists and Riivolution XML from the prebuilt features.

    python3 tools/build.py            # writes codes/<ID>.ini, codes/<ID>.txt, riivolution/<ID>.xml

The patched-DOL path (tools/patcher.py, the GUI) uses the very same ops, so the
three install methods cannot disagree.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import features
from regions import REGIONS

ROOT = os.path.join(HERE, '..')

CREDIT = {'cc': 'quatric', 'gc': 'quatric', 'ccgc': 'quatric'}
BLURB = {
    'cc': ['Play with a Classic Controller: left stick moves, right stick is the brush pointer.',
           'A/B = A/B, X = 1, Y = 2, ZL/L = Nunchuk Z, ZR/R = Nunchuk C, +/-/HOME as labelled.',
           'Needs a Wii Remote with a Classic Controller attached.'],
    'gc': ['Play with a GameCube controller (any port): stick moves, C-stick is the brush pointer.',
           'A/B = A/B, X = 1, Y = 2, L = Nunchuk Z, R = Nunchuk C, Z = -, START = +, L+R+START = HOME.',
           'A Wii Remote must still be connected (it is only used for the connection).'],
    'ccgc': ['Both of the above in one code (they hook the same places, so only one of the three may be on).'],
}
COMBINED_WARNING = [
    '*These codes keep a few helper routines in low memory at 0x80001820-0x80003000.',
    '*Do not use them together with a loader\'s own Gecko code handler on a real Wii (it lives there too);',
    '*Dolphin is fine, and so is the patched disc image made by the patcher.',
]


def gecko_ini(region):
    lines = ['[Gecko]']
    for name in features.FEATURES:
        if not features.available(name, region):
            continue
        f = features.load(name, region)
        lines.append('$%s' % f.title)
        lines.append('*By %s' % CREDIT[name])
        lines.append('*%s (%s)' % (REGIONS[region]['label'], region))
        lines += ['*' + b for b in BLURB[name]]
        lines += COMBINED_WARNING
        lines += f.gecko_lines()
    return '\n'.join(lines) + '\n'


def riivolution_xml(region):
    r = REGIONS[region]
    out = ['<!-- %s: controller patches by quatric -->' % r['label'],
           '<wiidisc version="1" root="/">',
           '  <id game="%s" version="%d" />' % (region, r['version']),
           '  <options>',
           '    <section name="%s">' % r['label']]
    # the three variants hook the same places, so they are the choices of one option
    out.append('      <option name="Controller" default="1">')
    for name in features.FEATURES:
        if features.available(name, region):
            out.append('        <choice name="%s"><patch id="%s" /></choice>' % (features.TITLES[name], name))
    out.append('      </option>')
    out += ['    </section>', '  </options>']
    for name in features.FEATURES:
        if not features.available(name, region):
            continue
        f = features.load(name, region)
        out.append('  <patch id="%s">' % name)
        out += ['    ' + e for e in f.memory_elements()]
        out.append('  </patch>')
    out.append('</wiidisc>')
    return '\n'.join(out) + '\n'


def main():
    for d in ('codes', 'riivolution'):
        os.makedirs(os.path.join(ROOT, d), exist_ok=True)
    for region in REGIONS:
        ini = gecko_ini(region)
        with open(os.path.join(ROOT, 'codes', region + '.ini'), 'w') as fh:
            fh.write(ini)
        # same codes in the plain cheat-file layout loaders read (no [Gecko] header)
        with open(os.path.join(ROOT, 'codes', region + '.txt'), 'w') as fh:
            fh.write(ini.split('\n', 1)[1])
        with open(os.path.join(ROOT, 'riivolution', region + '.xml'), 'w') as fh:
            fh.write(riivolution_xml(region))
        print(region, REGIONS[region]['label'])


if __name__ == '__main__':
    main()
