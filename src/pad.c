/* Classic Controller / GameCube controller -> Wii Remote + Nunchuk.
 *
 * Okami reads its pad straight from WPADRead (no KPAD), and only plays properly
 * when WPADProbe says a Nunchuk is attached.  This hook runs at the end of
 * WPADRead with r30 = the WPADStatus the game is about to look at and
 * rewrites it, so everything downstream sees an ordinary Wii Remote + Nunchuk:
 *
 *   buttons   0x00  Wii Remote button bits (Nunchuk C/Z are 0x4000/0x2000)
 *   accel     0x02  3 x s16
 *   IR dots   0x08  4 x 8 bytes: x, y (u16), size, index
 *   device    0x28  1 = Nunchuk, 2 = Classic Controller
 *   extension 0x2A  Nunchuk: accel 3 x s16, stick x, stick y (s8)
 *                   Classic Controller: buttons, 4 sticks (s16), 2 triggers
 *
 * The right stick drives the IR pointer (the Celestial Brush cursor) by moving a
 * pair of fake sensor-bar dots across the camera's field of view.
 *
 * Built with -DMODE=<bit 0: Classic Controller, bit 1: GameCube controller>.
 * Self-contained: no globals, no calls into the game.
 *
 * The Wii's SI registers sit at 0xCD006400, not the 0xCC006400 the GameCube
 * (and Dolphin, which mirrors both) uses: stores through the 0xCC alias are
 * silently dropped on a real console.
 */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef signed short s16;

#define M_CC 1
#define M_GC 2

#define SI_BASE 0xCD006400u
#define SI_OUT(c) (*(volatile u32 *)(SI_BASE + 12 * (c)))
#define SI_INH(c) (*(volatile u32 *)(SI_BASE + 4 + 12 * (c)))
#define SI_INL(c) (*(volatile u32 *)(SI_BASE + 8 + 12 * (c)))
#define SI_POLL (*(volatile u32 *)(SI_BASE + 0x30))
#define SI_SR (*(volatile u32 *)(SI_BASE + 0x38))

#define POLL_CMD 0x00400300u /* "status request", analog mode 3, no rumble */

/* WPADStatus offsets */
#define B_BTN 0x00
#define B_ACC 0x02
#define B_OBJ 0x08
#define B_DEV 0x28
#define B_ERR 0x29
#define B_EXT 0x2A
#define B_NSTK 0x30 /* Nunchuk stick: x, then y */

/* Classic Controller report inside the status */
#define CL_BTN 0x2A
#define CL_LX 0x2C
#define CL_LY 0x2E
#define CL_RX 0x30
#define CL_RY 0x32

/* Wii Remote button bits */
#define W_LEFT 0x0001
#define W_RIGHT 0x0002
#define W_DOWN 0x0004
#define W_UP 0x0008
#define W_PLUS 0x0010
#define W_TWO 0x0100
#define W_ONE 0x0200
#define W_B 0x0400
#define W_A 0x0800
#define W_MINUS 0x1000
#define W_Z 0x2000
#define W_C 0x4000
#define W_HOME 0x8000

/* Classic Controller button bits as the Wii Remote reports them */
#define CC_UP 0x0001
#define CC_LEFT 0x0002
#define CC_ZR 0x0004
#define CC_X 0x0008
#define CC_A 0x0010
#define CC_Y 0x0020
#define CC_B 0x0040
#define CC_ZL 0x0080
#define CC_R 0x0200
#define CC_PLUS 0x0400
#define CC_HOME 0x0800
#define CC_MINUS 0x1000
#define CC_L 0x2000
#define CC_DOWN 0x4000
#define CC_RIGHT 0x8000

/* GameCube pad button word (the high half of the first response word) */
#define PAD_LEFT 0x0001
#define PAD_RIGHT 0x0002
#define PAD_DOWN 0x0004
#define PAD_UP 0x0008
#define PAD_Z 0x0010
#define PAD_R 0x0020
#define PAD_L 0x0040
#define PAD_A 0x0100
#define PAD_B 0x0200
#define PAD_X 0x0400
#define PAD_Y 0x0800
#define PAD_START 0x1000

/* IR camera geometry measured from a real Wii Remote: the two sensor-bar dots
 * sit 0x89 apart around x = 0x1FF, y = 0x13B when the remote points at the
 * middle of the screen; the whole screen is about +-0x130 / +-0xF0 from there. */
#define IR_CX 0x1FF
#define IR_CY 0x13B
#define IR_HALF_W 0x130
#define IR_HALF_H 0xF0
#define IR_DOT_R 0x44
#define IR_DOT_L 0x45

#ifdef DEBUG_COUNTERS /* lab builds only: calls, classic seen, pad seen */
#define DBG(i) (((volatile u32 *)DEBUG_COUNTERS)[(i)]++)
#else
#define DBG(i) ((void)0)
#endif

static inline u16 rd16(const u8 *p) { return (u16)((p[0] << 8) | p[1]); }
static inline void wr16(u8 *p, u16 v) { p[0] = v >> 8; p[1] = v; }

static inline int clamp(int v, int lim)
{
    return v > lim ? lim : v < -lim ? -lim : v;
}

/* Dead zone, then scale to +-127. `range` is the full-deflection value. */
static inline int stick8(int v, int dead, int range)
{
    if (v > -dead && v < dead)
        return 0;
    v = v > 0 ? v - dead : v + dead;
    return clamp(v * 127 / (range - dead), 127);
}

/* Keep the auto-poller running on all four ports and the error flags cleared
 * (a latched NOREP from an unplug would otherwise hide the pad forever). */
static inline void poller(void)
{
    u32 p;
    int c;

    for (c = 0; c < 4; c++)
        if (SI_OUT(c) != POLL_CMD)
            SI_OUT(c) = POLL_CMD;
    SI_SR = (SI_SR & 0x0F0F0F0Fu) | 0x80000000u;
    p = SI_POLL;
    if ((p & 0xFF) != 0xFF || !(p & 0xFF00)) {
        p |= 0xFF;
        if (!(p & 0xFF00))
            p |= 0x0100;
        SI_POLL = p;
    }
}

struct input {
    u16 w;         /* Wii Remote button bits to add */
    int lx, ly;    /* left stick, +-127, up/right positive */
    int rx, ry;    /* right stick */
};

static inline void from_classic(const u8 *b, struct input *in)
{
    u16 c = rd16(b + CL_BTN);
    u16 w = 0;

    if (c & CC_A) w |= W_A;
    if (c & CC_B) w |= W_B;
    if (c & CC_X) w |= W_ONE;
    if (c & CC_Y) w |= W_TWO;
    if (c & (CC_ZL | CC_L)) w |= W_Z;
    if (c & (CC_ZR | CC_R)) w |= W_C;
    if (c & CC_PLUS) w |= W_PLUS;
    if (c & CC_MINUS) w |= W_MINUS;
    if (c & CC_HOME) w |= W_HOME;
    if (c & CC_UP) w |= W_UP;
    if (c & CC_DOWN) w |= W_DOWN;
    if (c & CC_LEFT) w |= W_LEFT;
    if (c & CC_RIGHT) w |= W_RIGHT;
    in->w = w;
    in->lx = stick8((s16)rd16(b + CL_LX), 40, 480);
    in->ly = stick8((s16)rd16(b + CL_LY), 40, 480);
    in->rx = stick8((s16)rd16(b + CL_RX), 40, 460);
    in->ry = stick8((s16)rd16(b + CL_RY), 40, 460);
}

/* Returns 1 when a pad answered on one of the four ports. */
static inline int from_pad(struct input *in)
{
    u32 h = 0, l = 0, p;
    u16 b, w = 0;
    int c, found = 0;

    poller();
    for (c = 0; c < 4; c++) {
        h = SI_INH(c);
        l = SI_INL(c);
        if (!(h & 0x80000000u) && (h & 0x00800000u)) {
            found = 1;
            break;
        }
    }
    if (!found)
        return 0;
    p = h >> 16;
    b = p;
    if (b & PAD_A) w |= W_A;
    if (b & PAD_B) w |= W_B;
    if (b & PAD_X) w |= W_ONE;
    if (b & PAD_Y) w |= W_TWO;
    if (b & PAD_L) w |= W_Z;
    if (b & PAD_R) w |= W_C;
    if (b & PAD_Z) w |= W_MINUS;
    if (b & PAD_START) w |= W_PLUS;
    if (b & PAD_UP) w |= W_UP;
    if (b & PAD_DOWN) w |= W_DOWN;
    if (b & PAD_LEFT) w |= W_LEFT;
    if (b & PAD_RIGHT) w |= W_RIGHT;
    if ((b & (PAD_L | PAD_R | PAD_START)) == (PAD_L | PAD_R | PAD_START))
        w |= W_HOME;
    in->w = w;
    in->lx = stick8((int)((h >> 8) & 0xFF) - 128, 12, 100);
    in->ly = stick8((int)(h & 0xFF) - 128, 12, 100);
    in->rx = stick8((int)(l >> 24) - 128, 12, 90);
    in->ry = stick8((int)((l >> 16) & 0xFF) - 128, 12, 90);
    return 1;
}

static inline void put_obj(u8 *o, u16 x, u16 y, u8 size, u8 idx)
{
    wr16(o, x);
    wr16(o + 2, y);
    o[4] = 0;
    o[5] = size;
    o[6] = idx;
    o[7] = 0;
}

static inline void apply(u8 *b, const struct input *in, int keep_remote_ir)
{
    int cx, cy, i;
    u16 w = rd16(b + B_BTN) | in->w;

    wr16(b + B_BTN, w);
    if (!rd16(b + B_ACC) && !rd16(b + B_ACC + 2) && !rd16(b + B_ACC + 4))
        wr16(b + B_ACC + 4, 0x68);                 /* resting remote, buttons up */
    (void)keep_remote_ir;
    /* the pointer: two dots, as a sensor bar would give */
    cx = IR_CX - in->rx * IR_HALF_W / 127;
    cy = IR_CY + in->ry * IR_HALF_H / 127;
    put_obj(b + B_OBJ, cx + IR_DOT_L, cy, 0x0C, 0);
    put_obj(b + B_OBJ + 8, cx - IR_DOT_R, cy, 0x0C, 1);
    put_obj(b + B_OBJ + 16, 0, 0x2FF, 0, 2);
    put_obj(b + B_OBJ + 24, 0, 0x2FF, 0, 3);
    /* Nunchuk extension */
    for (i = 0; i < 8; i++)
        b[B_EXT + i] = 0;
    b[B_EXT + 5] = 0xCC;
    b[B_NSTK] = (u8)in->lx;
    b[B_NSTK + 1] = (u8)in->ly;
    b[B_DEV] = 1;
    b[B_ERR] = 0;
}

void pad_hook(u8 *b)
{
    struct input in;
    int have = 0;

    in.w = 0;
    in.lx = in.ly = in.rx = in.ry = 0;
#if MODE & M_CC
    if (b[B_DEV] == 2) {
        DBG(0);
        from_classic(b, &in);
        have = 1;
    }
#endif
#if MODE & M_GC
    struct input pad;

    if (from_pad(&pad)) {
        DBG(1);
        in.w |= pad.w;
        if (pad.lx || pad.ly) {
            in.lx = pad.lx;
            in.ly = pad.ly;
        }
        if (pad.rx || pad.ry) {
            in.rx = pad.rx;
            in.ry = pad.ry;
        }
        have = 1;
    }
#endif
    if (have)
        apply(b, &in, 0);
}
