"""The three retail releases of Okami (Wii) and where their pieces are.

DOL sizes identify a stock main.dol; every hook site is carried from the USA
build to the others by a masked signature search (see sig.py).
"""
REGIONS = {
    'ROWE08': dict(label='Okami (USA)', short='USA', version=0),
    'ROWP08': dict(label='Okami (Europe)', short='Europe', version=0),
    'ROWJ08': dict(label='Okami (Japan)', short='Japan', version=0),
}

# retail DOL sizes, to give a clear error on someone else's modified dump
DOL_SIZES = {'ROWE08': 1707040, 'ROWP08': 1707968, 'ROWJ08': 1743136}
