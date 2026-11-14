# Okami Patch

Play **Okami** (Wii) with a **Classic Controller** or a **GameCube controller**
instead of a Wii Remote + Nunchuk. Works with the USA (`ROWE08`), European
(`ROWP08`) and Japanese (`ROWJ08`) releases. Each patch is optional.

The patches are applied to your own copy of the game: drop a clean `.wbfs` or
`.iso` onto the patcher and play the result on a Wii (USB loader) or in Dolphin.
Nothing from the game is included in this repository.

## How it works

Okami reads its pad straight from `WPADRead` and only plays properly when
`WPADProbe` reports a Nunchuk. The patch hooks the end of `WPADRead` and rewrites
the status the game is about to read so it looks like a Wii Remote + Nunchuk:
buttons, Nunchuk stick, and a pair of fake sensor-bar dots for the IR pointer
(the Celestial Brush cursor). For a Classic Controller the extension is also
announced as a Nunchuk; the stick and button data are taken from the SDK's own
copy of the status, since the game only receives the Nunchuk-sized part. For a
GameCube controller the SI hardware is polled directly.

## Controls

| Pad | Move | Brush pointer | A / B | 1 / 2 | Nunchuk Z / C | + / - / HOME |
|---|---|---|---|---|---|---|
| Classic Controller | left stick | right stick | A / B | X / Y | ZL or L / ZR or R | + / - / HOME |
| GameCube controller | stick | C-stick | A / B | X / Y | L / R | START / Z / L+R+START |

The D-pad is the D-pad. The right stick / C-stick positions the pointer
absolutely (centre = middle of the screen).

## Status

Verified in Dolphin on all three releases: the status the game receives for
every button, both sticks and the pointer, for a Classic Controller, a GameCube
pad, and both together, with no crash when the stick is moved on the title
screen. The USA release was also played with the Classic Controller (title
screen, New Game, pause menu, Amaterasu walking with the left stick). **Not
tested on a real Wii, and the Celestial Brush is not checked (it is locked at the
start of the game).**

- a Wii Remote must stay connected (also with the GameCube pad)
- plug the GameCube pad in before starting the game
- the Wii Remote's own motion is still read: swing it for motion-only actions

## Using it

- **Patched disc:** `python3 tools/gui.py` (or the packaged app), or
  `python3 tools/patch_disc.py "Okami (USA).wbfs" --cc --gc`. Needs
  [wit](https://wit.wiimm.de/) on `PATH`. The original is kept as `<name>.bak`.
- **Gecko codes:** `codes/<ID>.ini` (Dolphin) or `codes/<ID>.txt`.
- **Riivolution:** `riivolution/<ID>.xml`.

The Gecko/Riivolution forms keep their routines in low memory at
`0x80001820-0x80003000`; do not combine them with a loader's own code handler on
a real Wii.

## Building

```
OKAMI_DOLS=<dir with ROWE08.dol ROWP08.dol ROWJ08.dol> python3 tools/gen_prebuilt.py   # needs devkitPPC
python3 tools/build.py        # codes/ and riivolution/
python3 tools/check.py        # consistency checks
OKAMI_DOLS=... python3 tools/verify.py
```

`lab/` holds the Dolphin test harness (GDB-stub memory access, pipe input).
