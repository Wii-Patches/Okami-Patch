# Entry stub for pad.c, placed right after it in the injected section.  Runs at
# the instruction that hands WPADRead's interrupt state back to OSRestoreInterrupts,
# with @BUF@ = the register holding the WPADStatus being returned.
# Saves everything the C code might touch, calls pad_hook(r30), restores, then
# runs the displaced instruction.
    .globl stub
stub:
    stwu    1, -0x90(1)
    stw     0, 0x08(1)
    stw     3, 0x0C(1)
    stw     4, 0x10(1)
    stw     5, 0x14(1)
    stw     6, 0x18(1)
    stw     7, 0x1C(1)
    stw     8, 0x20(1)
    stw     9, 0x24(1)
    stw     10, 0x28(1)
    stw     11, 0x2C(1)
    stw     12, 0x30(1)
    mflr    0
    stw     0, 0x34(1)
    mfcr    0
    stw     0, 0x38(1)
    mfctr   0
    stw     0, 0x3C(1)
    mfxer   0
    stw     0, 0x40(1)
    mr      3, @BUF@
    bl      pad_hook
    lwz     0, 0x40(1)
    mtxer   0
    lwz     0, 0x3C(1)
    mtctr   0
    lwz     0, 0x38(1)
    mtcr    0
    lwz     0, 0x34(1)
    mtlr    0
    lwz     3, 0x0C(1)
    lwz     4, 0x10(1)
    lwz     5, 0x14(1)
    lwz     6, 0x18(1)
    lwz     7, 0x1C(1)
    lwz     8, 0x20(1)
    lwz     9, 0x24(1)
    lwz     10, 0x28(1)
    lwz     11, 0x2C(1)
    lwz     12, 0x30(1)
    lwz     0, 0x08(1)
    addi    1, 1, 0x90
    @DISPLACED@
