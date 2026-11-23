"""Render The Daily Compass front page for Monday 23 November 2026.

Art-led front page of 40 verified stories: three lead cards with large
scene illustrations under bold headlines, twelve illustrated panels with
bold headlines, and a readable numbered index for the rest. Every story
was first reported on Monday 23 Nov 2026, or is labelled in the poster
as a weekend result carried as such. Honesty devices: a source outlet
on every story, a key-numbers strip of verified figures only, a regions
bar computed from the final story list, and a DATE CHECK box fencing
off other days' news. Output is deterministic: the same code always
writes byte-identical PNG bytes.
"""

import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
M = 16  # margin

PAPER = (247, 241, 227)
INK = (24, 22, 18)
MUTED = (96, 88, 72)
PANEL = (255, 253, 246)
EDGE = (58, 52, 40)
RED = (178, 44, 36)
BADGE = (164, 32, 28)
WHITE = (255, 255, 255)
SEA = (196, 216, 228)
LAND = (170, 190, 150)
LAND_EDGE = (120, 140, 105)
GOLD = (176, 128, 24)
BLUE = (38, 84, 140)
GREEN = (38, 110, 72)
DARK = (28, 32, 44)
SKY = (210, 224, 238)

FD = Path("/usr/share/fonts/truetype/dejavu")
SERIF = str(FD / "DejaVuSerif-Bold.ttf")
SANS = str(FD / "DejaVuSans.ttf")
SANSB = str(FD / "DejaVuSans-Bold.ttf")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "poster.png"


def ft(path, size):
    return ImageFont.truetype(path, size)


def tw(d, text, font):
    return d.textlength(text, font=font)


def wrap(d, text, font, maxw):
    """Greedy word wrap; pulls a lone last word up when it fits."""
    lines, cur = [], ""
    for word in text.split():
        trial = word if not cur else cur + " " + word
        if tw(d, trial, font) <= maxw:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    while len(lines) >= 2:
        last, prev = lines[-1].split(), lines[-2].split()
        if len(last) > 1 or len(prev) < 2:
            break
        joined = prev[-1] + " " + lines[-1]
        if tw(d, joined, font) > maxw:
            break
        lines[-2] = " ".join(prev[:-1])
        lines[-1] = joined
    return lines


def wrap_tagged(d, text, tag, font, maxw):
    """Wrap text, then append the source tag in the same flow.

    Returns [(line, tag_start)] with tag_start -1 for a plain line, 0
    for a line drawn wholly in the muted tag colour, or the character
    index where the muted tag begins on that line.
    """
    lines = wrap(d, text, font, maxw)
    merged = lines[-1] + " " + tag
    if tw(d, merged, font) <= maxw:
        start = len(lines[-1]) + 1
        lines[-1] = merged
        return [(ln, start if i == len(lines) - 1 else -1)
                for i, ln in enumerate(lines)]
    extra = wrap(d, tag, font, maxw)
    return [(ln, -1) for ln in lines] + [(ln, 0) for ln in extra]


def para(d, x, y, text, font, maxw, leading, color=INK, max_lines=None):
    lines = wrap(d, text, font, maxw)
    if max_lines is not None:
        lines = lines[:max_lines]
    for ln in lines:
        d.text((x, y), ln, font=font, fill=color)
        y += leading
    return y


def badge(d, x, y, num, r=13):
    d.ellipse([x - r, y - r, x + r, y + r], fill=BADGE,
              outline=WHITE, width=2)
    t = str(num)
    fn = ft(SANSB, 15 if len(t) == 1 else 12)
    w = tw(d, t, fn)
    d.text((x - w / 2, y - 8 if len(t) == 1 else y - 7), t, font=fn,
           fill=WHITE)


def frame(d, box):
    x0, y0, x1, y1 = box
    d.rectangle([x0, y0, x1, y1], fill=PANEL, outline=EDGE, width=2)


def hrule(d, x0, y, x1, w=2):
    d.line([(x0, y), (x1, y)], fill=INK, width=w)


def disc(d, cx, cy, r, fill, outline=None, width=1):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill,
              outline=outline, width=width)


def lcg(seed):
    """Deterministic pseudo-random stream (fixed seed)."""
    s = seed
    while True:
        s = (1103515245 * s + 12345) % (2 ** 31)
        yield s


def vgrad(d, x, y, w, h, top, bot, steps=14):
    for i in range(steps):
        t = i / (steps - 1)
        col = tuple(round(top[c] + (bot[c] - top[c]) * t) for c in range(3))
        y0 = y + h * i // steps
        y1 = y + h * (i + 1) // steps
        d.rectangle([x, y0, x + w, y1], fill=col)


def halo(d, cx, cy, r, cols):
    """Concentric glow, faintest outer ring first."""
    n = len(cols)
    for i, col in enumerate(cols):
        rr = r * (n - i) / n
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col)


def burst(d, cx, cy, r, col1, col2):
    for rr, col in ((r, col1), (int(r * 0.6), col2)):
        pts = []
        for a in range(16):
            ang = math.pi * a / 8
            rad = rr if a % 2 == 0 else rr * 0.5
            pts.append((cx + rad * math.cos(ang),
                        cy + rad * math.sin(ang)))
        d.polygon(pts, fill=col)


def arc_pts(p0, p1, p2, n=16):
    pts = []
    for i in range(n + 1):
        t = i / n
        px = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        py = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        pts.append((px, py))
    return pts


def dot_trail(d, pts, col, r=2, step=2):
    for i, (px, py) in enumerate(pts):
        if i % step == 0:
            d.ellipse([px - r, py - r, px + r, py + r], fill=col)


def stars(d, x, y, w, h, n, seed, frac=0.6):
    g = lcg(seed)
    for _ in range(n):
        px = x + next(g) % max(w - 4, 1)
        py = y + next(g) % max(int(h * frac), 1)
        d.ellipse([px, py, px + 2, py + 2], fill=(206, 213, 229))


def refl(d, x, y, w, col, n=3, gap=3, lh=2):
    for i in range(n):
        yy = y + i * (lh + gap)
        inset = (i % 2) * 2
        d.line([(x + inset, yy), (x + w - inset, yy)], fill=col, width=lh)


# --- lead scenes -------------------------------------------------------------

def scene_market(d, x, y, w, h):
    """A trading floor at the open: a big board with a plunging red
    line, traders in silhouette below, a green ticker crawling up."""
    vgrad(d, x, y, w, h, (14, 18, 34), (40, 44, 66), steps=22)
    # the big board
    bx, by = x + 10, y + 8
    bw, bh = w - 20, int(h * 0.52)
    d.rectangle([bx, by, bx + bw, by + bh], fill=(8, 12, 24),
                outline=(90, 100, 130), width=2)
    for gx in range(bx + 12, bx + bw - 4, 18):
        d.line([(gx, by + 6), (gx, by + bh - 6)], fill=(32, 42, 66), width=1)
    for gy in range(by + 10, by + bh - 8, 14):
        d.line([(bx + 6, gy), (bx + bw - 6, gy)], fill=(32, 42, 66), width=1)
    pts = [(bx + 8, by + 18), (bx + 30, by + 14), (bx + 52, by + 26),
           (bx + 74, by + 24), (bx + 96, by + 40), (bx + 118, by + 54),
           (bx + 140, by + 66), (bx + 164, by + 78)]
    d.line(pts, fill=(110, 36, 30), width=6)
    d.line(pts, fill=(240, 84, 60), width=2)
    for px, py in pts:
        d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(255, 170, 140))
    ex, ey = pts[-1]
    d.polygon([(ex - 5, ey + 2), (ex + 7, ey + 3), (ex + 1, ey + 13)],
              fill=(240, 84, 60))
    # a small green bounce at the board's edge: futures rebounding
    d.line([(bx + bw - 44, by + bh - 12), (bx + bw - 26, by + bh - 22),
            (bx + bw - 8, by + bh - 16)], fill=(60, 200, 120), width=2)
    # ticker tape under the board
    ty = by + bh + 8
    d.rectangle([x + 6, ty, x + w - 6, ty + 12], fill=(20, 24, 40))
    g = lcg(7)
    for i in range(9):
        tx = x + 10 + i * (w - 20) // 9
        col = (240, 84, 60) if next(g) % 3 else (60, 200, 120)
        d.rectangle([tx, ty + 3, tx + 12, ty + 9], fill=col)
    # traders in silhouette, one pointing at the board, one on the phone
    base = y + h
    for cx, suit, arm in ((0.16, (10, 12, 20), "up"),
                          (0.38, (16, 14, 26), "down"),
                          (0.62, (12, 16, 24), "phone"),
                          (0.84, (14, 12, 22), "up")):
        px = x + int(w * cx)
        d.pieslice([px - 16, base - 52, px + 16, base - 12], 180, 360,
                   fill=suit)
        disc(d, px, base - 56, 9, (210, 180, 150))
        if arm == "up":
            d.line([(px + 12, base - 34), (px + 30, base - 62)],
                   fill=suit, width=4)
        elif arm == "down":
            d.line([(px + 12, base - 34), (px + 26, base - 14)],
                   fill=suit, width=4)
        else:
            d.line([(px + 12, base - 34), (px + 20, base - 52)],
                   fill=suit, width=4)
            d.rectangle([px + 18, base - 58, px + 26, base - 48],
                        fill=(30, 30, 36))
    d.line([(x, base - 2), (x + w, base - 2)], fill=(90, 100, 130), width=1)


def scene_summit(d, x, y, w, h):
    """A Delhi meeting room: two flags, a long table, two leaders
    shaking hands across it, delegates behind."""
    vgrad(d, x, y, w, h, (242, 232, 206), (216, 198, 166), steps=18)
    # chandeliers
    for fx_ in (0.14, 0.50, 0.86):
        cx = x + int(w * fx_)
        d.line([(cx, y), (cx, y + 8)], fill=(120, 100, 64), width=2)
        halo(d, cx, y + 13, 10, [(226, 208, 164), (236, 220, 182)])
        disc(d, cx, y + 13, 4, (252, 240, 200), outline=(150, 124, 78))
    # Nepal flag (crimson pennants) on the left pole
    fx = x + 14
    d.line([(fx, y + 10), (fx, y + 66)], fill=(90, 80, 60), width=2)
    d.polygon([(fx, y + 12), (fx + 26, y + 22), (fx, y + 32)],
              fill=(190, 40, 50))
    d.polygon([(fx, y + 32), (fx + 22, y + 40), (fx, y + 48)],
              fill=(190, 40, 50))
    d.line([(fx, y + 12), (fx, y + 48)], fill=(40, 60, 160), width=2)
    # India flag (saffron, white, green) on the right pole
    fx = x + w - 40
    d.line([(fx, y + 10), (fx, y + 66)], fill=(90, 80, 60), width=2)
    for i, col in enumerate(((230, 120, 40), (246, 242, 232),
                             (30, 130, 70))):
        d.rectangle([fx, y + 12 + i * 11, fx + 26, y + 23 + i * 11],
                    fill=col)
    disc(d, fx + 13, y + 28, 5, None, outline=(30, 60, 140), width=1)
    # back-wall emblem: a globe between the flags
    gx, gy = x + int(w * 0.50), y + 38
    d.ellipse([gx - 30, gy - 30, gx + 30, gy + 30], fill=(246, 238, 214))
    disc(d, gx, gy, 24, (74, 142, 192), outline=(52, 96, 140), width=2)
    d.ellipse([gx - 17, gy - 12, gx - 3, gy + 1], fill=GREEN)
    d.ellipse([gx + 2, gy + 5, gx + 18, gy + 16], fill=GREEN)
    d.ellipse([gx - 8, gy - 24, gx + 8, gy + 24], outline=(52, 96, 140))
    d.line([(gx - 24, gy), (gx + 24, gy)], fill=(52, 96, 140), width=1)
    # floor and the long table in perspective
    ty = y + h - 46
    d.rectangle([x, ty + 18, x + w, y + h], fill=(158, 124, 80))
    d.polygon([(x + 18, y + h - 2), (x + w - 18, y + h - 2),
               (x + int(w * 0.66), ty), (x + int(w * 0.34), ty)],
              fill=(146, 106, 66))
    d.polygon([(x + 34, y + h - 8), (x + w - 34, y + h - 8),
               (x + int(w * 0.64), ty + 4), (x + int(w * 0.36), ty + 4)],
              fill=(160, 120, 76))
    # the two leaders leaning in to shake hands across the table:
    # shoulders and heads above the table, forearms meeting in a
    # clear clasp at the centre
    skins = [(196, 142, 102), (233, 192, 152)]
    suits = [(38, 44, 66), (74, 60, 54)]
    for i, cx_ in enumerate((0.38, 0.62)):
        cx = x + int(w * cx_)
        cy = ty - 10
        d.pieslice([cx - 14, cy - 4, cx + 14, cy + 18], 180, 360,
                   fill=suits[i])
        disc(d, cx, cy - 9, 8, skins[i])
        d.rectangle([cx - 7, ty + 5, cx + 7, ty + 11],
                    fill=(245, 243, 236))
    hx = x + int(w * 0.50)
    d.line([(x + int(w * 0.38) + 11, ty - 4), (hx - 4, ty - 14)],
           fill=suits[0], width=5)
    d.line([(x + int(w * 0.62) - 11, ty - 4), (hx + 4, ty - 14)],
           fill=suits[1], width=5)
    disc(d, hx, ty - 14, 6, (240, 205, 168), outline=(120, 90, 60),
         width=1)
    d.line([(hx - 5, ty - 16), (hx + 5, ty - 12)], fill=(120, 90, 60),
           width=1)
    d.line([(hx - 5, ty - 12), (hx + 5, ty - 16)], fill=(120, 90, 60),
           width=1)
    # delegates along the far side
    for i in range(6):
        cx = x + int(w * (0.08 + 0.84 * i / 5))
        if abs(cx - x - int(w * 0.50)) < 26:
            continue
        cy = ty - 6
        d.pieslice([cx - 11, cy - 3, cx + 11, cy + 16], 180, 360,
                   fill=((52, 66, 52), (86, 44, 48), (44, 52, 74))[i % 3])
        disc(d, cx, cy - 6, 6, skins[i % 2])
        d.rectangle([cx - 6, ty + 6, cx + 6, ty + 11],
                    fill=(245, 243, 236))
    # near-side delegates seen from behind
    for cx, col, suit in ((x + int(w * 0.07), (42, 34, 30), (36, 38, 46)),
                          (x + int(w * 0.93), (96, 74, 52), (40, 46, 40))):
        d.pieslice([cx - 23, y + h - 15, cx + 23, y + h + 21], 180, 360,
                   fill=suit)
        disc(d, cx, y + h - 5, 10, col)


def scene_tanker(d, x, y, w, h):
    """Dusk in the Gulf of Finland: a cargo ship burning at the
    waterline, a tugboat towing it, smoke over a grey sea."""
    vgrad(d, x, y, w, h, (88, 96, 116), (196, 178, 150), steps=22)
    stars(d, x, y, w, h, 20, 5, frac=0.25)
    gy = y + h - 34
    # smoke plumes from the ship's deck
    for sx_, sy_, sw in ((0.42, 0.55, 34), (0.55, 0.48, 28), (0.30, 0.60, 24)):
        sx0 = x + int(w * sx_)
        sy0 = y + int(h * sy_)
        for k in range(3):
            d.ellipse([sx0 + k * 9, sy0 - k * 7,
                       sx0 + k * 9 + sw - k * 5, sy0 - k * 7 + 12],
                      fill=(70 + k * 10, 70 + k * 10, 78 + k * 8))
    # the burning cargo ship, listing slightly
    sx0, sy0 = x + int(w * 0.22), gy - 26
    sw_, sh_ = int(w * 0.52), 26
    d.polygon([(sx0, sy0 + 8), (sx0 + sw_, sy0 + 8), (sx0 + sw_ - 12, gy),
               (sx0 + 14, gy)], fill=(60, 44, 40))
    d.rectangle([sx0 + 6, sy0 - 2, sx0 + sw_ - 6, sy0 + 8],
                fill=(40, 40, 46))
    for cx_ in range(sx0 + 14, sx0 + sw_ - 10, 18):
        d.rectangle([cx_, sy0 - 12, cx_ + 12, sy0 - 2], fill=(150, 60, 40))
    # flames along the deck
    for fx_ in (0.30, 0.42, 0.54, 0.66):
        ex = x + int(w * fx_)
        halo(d, ex, sy0 - 6, 14, [(120, 70, 30), (170, 95, 34)])
        burst(d, ex, sy0 - 8, 9, (238, 128, 34), (252, 224, 130))
    # bridge tower at the stern, windows lit
    d.rectangle([sx0 + sw_ - 34, sy0 - 26, sx0 + sw_ - 8, sy0 - 2],
                fill=(52, 52, 58))
    for wy in range(sy0 - 23, sy0 - 4, 6):
        d.rectangle([sx0 + sw_ - 31, wy, sx0 + sw_ - 25, wy + 3],
                    fill=(244, 200, 92))
    # the tugboat ahead, towing line taut between them
    tx0 = x + int(w * 0.80)
    d.line([(sx0 + sw_ - 4, sy0 + 4), (tx0 - 4, gy - 8)],
           fill=(30, 28, 26), width=2)
    d.polygon([(tx0, gy - 6), (tx0 + 34, gy - 6), (tx0 + 28, gy + 8),
               (tx0 + 4, gy + 8)], fill=(30, 34, 44))
    d.rectangle([tx0 + 6, gy - 18, tx0 + 22, gy - 6], fill=(200, 60, 40))
    d.rectangle([tx0 + 10, gy - 14, tx0 + 18, gy - 10],
                fill=(244, 200, 92))
    d.line([(tx0 + 24, gy - 18), (tx0 + 24, gy - 30)], fill=(30, 30, 36),
           width=2)
    d.line([(tx0 + 24, gy - 30), (tx0 + 30, gy - 24)], fill=(30, 30, 36),
           width=1)
    # the sea, with fire reflections under the ship
    vgrad(d, x, gy, w, h - (gy - y), (60, 74, 92), (28, 36, 52), steps=8)
    refl(d, x + int(w * 0.30), gy + 5, 60, (180, 110, 50), n=3)
    refl(d, x + int(w * 0.55), gy + 8, 40, (150, 90, 40), n=2)
    refl(d, tx0, gy + 12, 30, (120, 120, 130), n=2)
    d.line([(x, gy), (x + w, gy)], fill=(110, 120, 132), width=1)


SCENES = {"market": scene_market, "summit": scene_summit,
          "tanker": scene_tanker}

# --- pictograms: small scenes drawn with primitives --------------------------

def art_fire(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(52, 44, 40))
    # factory block with a sawtooth roof
    d.rectangle([x + 8, y + 44, x + w - 8, y + h - 10], fill=(30, 30, 34))
    for i in range(3):
        bx = x + 12 + i * 26
        d.polygon([(bx, y + 44), (bx + 13, y + 32), (bx + 26, y + 44)],
                  fill=(40, 40, 44))
    d.rectangle([x + w - 22, y + 18, x + w - 14, y + 44], fill=(60, 56, 52))
    for wy in range(y + 52, y + h - 14, 10):
        for wx in range(x + 14, x + w - 14, 12):
            d.rectangle([wx, wy, wx + 5, wy + 4], fill=(244, 200, 92))
    # flames and smoke above the roof
    for fx_ in (0.30, 0.50, 0.70):
        ex, ey = x + int(w * fx_), y + 30
        halo(d, ex, ey, 12, [(120, 70, 30), (170, 95, 34)])
        burst(d, ex, ey, 8, (238, 128, 34), (252, 224, 130))
    for k in range(3):
        d.ellipse([x + 30 + k * 10, y + 6 - k * 2,
                   x + 52 + k * 10, y + 16 - k * 2],
                  fill=(90 + k * 8, 90 + k * 8, 96 + k * 8))


def art_podium(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(226, 232, 240))
    # a lectern with a microphone, and a resigning minister stepping away
    d.polygon([(x + 30, y + h - 12), (x + 70, y + h - 12),
               (x + 62, y + 46), (x + 38, y + 46)], fill=(60, 52, 44))
    d.rectangle([x + 26, y + 40, x + 74, y + 48], fill=(44, 38, 32))
    d.line([(x + 50, y + 40), (x + 62, y + 24)], fill=(40, 40, 44), width=2)
    disc(d, x + 64, y + 22, 4, (30, 30, 36))
    # a paper on the lectern: the resignation letter
    d.polygon([(x + 34, y + 42), (x + 48, y + 42), (x + 46, y + 30),
               (x + 36, y + 30)], fill=(248, 246, 238))
    d.line([(x + 38, y + 36), (x + 44, y + 36)], fill=INK, width=1)
    # the minister, head bowed, walking off to the right
    cx, cy = x + w - 22, y + h - 30
    disc(d, cx, cy - 22, 7, (196, 142, 102))
    d.pieslice([cx - 11, cy - 14, cx + 11, cy + 8], 180, 360,
               fill=(38, 44, 66))
    d.line([(cx - 8, cy + 6), (cx - 14, cy + 16)], fill=(30, 30, 36), width=3)
    d.line([(cx + 6, cy + 6), (cx + 12, cy + 16)], fill=(30, 30, 36), width=3)
    # a small flag on the wall behind
    d.rectangle([x + 10, y + 12, x + 26, y + 26], fill=(220, 60, 60))
    d.rectangle([x + 10, y + 12, x + 26, y + 19], fill=(40, 60, 160))


def art_factory(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(232, 228, 218))
    # factory with chimneys, and a red down-arrow over it
    d.rectangle([x + 10, y + 52, x + w - 10, y + h - 12], fill=(90, 96, 106))
    d.rectangle([x + 16, y + 30, x + 24, y + 52], fill=(70, 76, 86))
    d.rectangle([x + 30, y + 38, x + 38, y + 52], fill=(70, 76, 86))
    for wx in range(x + 16, x + w - 16, 12):
        d.rectangle([wx, y + 60, wx + 6, y + 66], fill=(244, 200, 92))
    for k in range(2):
        d.ellipse([x + 16 + k * 6, y + 22 - k * 6,
                   x + 30 + k * 6, y + 30 - k * 6],
                  fill=(150, 150, 156))
    ax, ay = x + w - 24, y + 12
    d.line([(ax - 8, ay), (ax + 6, ay + 12)], fill=RED, width=4)
    d.polygon([(ax + 1, ay + 6), (ax + 11, ay + 13), (ax + 2, ay + 17)],
              fill=RED)
    d.line([(x + 10, y + h - 12), (x + w - 10, y + h - 12)],
           fill=(70, 76, 86), width=3)


def art_gold(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(34, 28, 26))
    d.arc([x + 18, y + 6, x + w - 18, y + 70], 180, 360,
          fill=(110, 96, 84), width=3)

    def bar(bx, by, bw=26):
        d.polygon([(bx + 3, by), (bx + bw - 3, by), (bx + bw, by + 9),
                   (bx, by + 9)], fill=(196, 148, 40),
                  outline=(120, 84, 20))
        d.polygon([(bx + 3, by), (bx + bw - 3, by), (bx + bw - 6, by + 4),
                   (bx + 6, by + 4)], fill=(246, 205, 92))

    base = y + h - 16
    for i in range(3):
        bar(x + 12 + i * 28, base - 10)
    for i in range(2):
        bar(x + 26 + i * 28, base - 21)
    bar(x + 40, base - 32)
    d.line([(x + 6, base + 2), (x + w - 6, base + 2)],
           fill=(110, 96, 84), width=2)
    ax, ay = x + w - 20, y + 12
    d.line([(ax - 8, ay), (ax + 6, ay + 12)], fill=RED, width=4)
    d.polygon([(ax + 1, ay + 6), (ax + 11, ay + 13), (ax + 2, ay + 17)],
              fill=RED)


def art_database(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(222, 228, 240))
    d.rectangle([x + 8, y + 26, x + 26, y + h - 14], fill=(104, 122, 158))
    for ry in range(y + 34, y + h - 20, 10):
        d.line([(x + 11, ry), (x + 23, ry)], fill=WHITE, width=2)
    cx, cy = x + w // 2 + 8, y + h // 2 - 4
    d.ellipse([cx - 26, cy - 26, cx + 26, cy - 12], fill=(90, 110, 150))
    d.rectangle([cx - 26, cy - 19, cx + 26, cy + 22], fill=(120, 140, 180))
    d.ellipse([cx - 26, cy + 8, cx + 26, cy + 22], fill=(90, 110, 150))
    d.line([(cx - 26, cy - 4), (cx + 26, cy - 4)], fill=WHITE, width=2)
    d.line([(cx - 26, cy + 8), (cx + 26, cy + 8)], fill=WHITE, width=2)
    d.rectangle([cx + 8, cy + 14, cx + 30, cy + 34], fill=GOLD,
                outline=INK, width=2)
    d.ellipse([cx + 15, cy + 19, cx + 23, cy + 27], outline=INK, width=2)
    tx, ty = x + w - 18, y + 12
    d.polygon([(tx, ty - 8), (tx + 8, ty + 6), (tx - 8, ty + 6)],
              fill=(240, 180, 40), outline=INK)
    d.line([(tx, ty - 3), (tx, ty + 2)], fill=INK, width=2)
    d.ellipse([tx - 1, ty + 3, tx + 1, ty + 5], fill=INK)


def art_card(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(232, 228, 220))
    cx, cy = x + w // 2, y + h // 2 - 4
    d.rectangle([cx - 38, cy - 22, cx + 38, cy + 22], fill=(38, 84, 140),
                outline=INK, width=2)
    d.rectangle([cx - 38, cy - 22, cx + 38, cy - 8], fill=(24, 60, 110))
    d.rectangle([cx - 30, cy + 2, cx - 16, cy + 12], fill=GOLD)
    d.line([(cx - 30, cy + 7), (cx - 16, cy + 7)], fill=(120, 84, 20),
           width=1)
    d.line([(cx - 23, cy + 2), (cx - 23, cy + 12)], fill=(120, 84, 20),
           width=1)
    for i in range(4):
        d.text((cx - 30 + i * 17, cy + 14), "••••", font=ft(SANSB, 7),
               fill=WHITE)
    # a red "10%" tag in the corner
    d.rectangle([x + w - 30, y + 8, x + w - 8, y + 24], fill=RED)
    d.text((x + w - 28, y + 10), "10%", font=ft(SANSB, 10), fill=WHITE)


def art_car(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(226, 236, 248))
    cx, cy = x + w // 2, y + h // 2 + 6
    # sedan side profile
    d.polygon([(cx - 40, cy + 8), (cx - 34, cy - 8), (cx - 14, cy - 16),
               (cx + 16, cy - 16), (cx + 34, cy - 6), (cx + 40, cy + 8)],
              fill=(90, 110, 150), outline=INK)
    d.rectangle([cx - 12, cy - 14, cx + 12, cy - 6], fill=SKY)
    disc(d, cx - 22, cy + 8, 9, (30, 30, 36))
    disc(d, cx + 22, cy + 8, 9, (30, 30, 36))
    disc(d, cx - 22, cy + 8, 4, (180, 184, 190))
    disc(d, cx + 22, cy + 8, 4, (180, 184, 190))
    d.line([(x + 6, cy + 18), (x + w - 6, cy + 18)], fill=INK, width=2)
    # warning triangle above the car
    tx, ty = x + w - 18, y + 14
    d.polygon([(tx, ty - 9), (tx + 9, ty + 7), (tx - 9, ty + 7)],
              fill=(240, 180, 40), outline=INK)
    d.line([(tx, ty - 4), (tx, ty + 2)], fill=INK, width=2)
    d.ellipse([tx - 1, ty + 3, tx + 1, ty + 5], fill=INK)


def art_chart(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(16, 22, 38))
    for gx in range(x + 10, x + w - 6, 16):
        d.line([(gx, y + 8), (gx, y + h - 20)], fill=(40, 52, 78), width=1)
    for gy in range(y + 10, y + h - 18, 14):
        d.line([(x + 6, gy), (x + w - 6, gy)], fill=(40, 52, 78), width=1)
    pts = [(x + 8, y + 22), (x + 26, y + 18), (x + 40, y + 30),
           (x + 54, y + 28), (x + 68, y + 46), (x + 82, y + 62),
           (x + 94, y + 74)]
    d.line(pts, fill=(120, 40, 34), width=5)
    d.line(pts, fill=(240, 84, 60), width=2)
    for px, py in pts:
        d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(255, 170, 140))
    ex, ey = pts[-1]
    d.polygon([(ex - 5, ey + 2), (ex + 6, ey + 3), (ex + 1, ey + 12)],
              fill=(240, 84, 60))
    for i, bh in enumerate((5, 6, 8, 7, 11, 14, 17)):
        bx = x + 8 + i * 13
        d.rectangle([bx, y + h - 6 - bh, bx + 7, y + h - 6],
                    fill=(70, 96, 140))


def art_climate(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(214, 232, 214))
    cx, cy, r = x + w // 2, y + h // 2, 30
    disc(d, cx, cy, r, (70, 140, 190))
    d.arc([cx - r, cy - r, cx + r, cy + r], 200, 340, fill=WHITE, width=4)
    d.arc([cx - r, cy - r, cx + r, cy + r], 20, 160, fill=WHITE, width=4)
    d.ellipse([cx - 22, cy - 14, cx - 2, cy + 2], fill=GREEN)
    d.ellipse([cx + 2, cy + 4, cx + 20, cy + 18], fill=GREEN)
    # a crack across the globe: talks that broke down
    d.line([(cx - 24, cy - 18), (cx - 8, cy - 2), (cx - 18, cy + 10),
            (cx + 2, cy + 22)], fill=(30, 30, 36), width=2)


def art_bridge(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=SKY)
    d.rectangle([x, y + h - 16, x + w, y + h], fill=(120, 150, 190))
    deck_y = y + h - 26
    for tx in (x + w // 4, x + 3 * w // 4):
        d.rectangle([tx - 3, y + 16, tx + 3, deck_y], fill=INK)
    d.arc([x + w // 4 - 3, y + 2, x + 3 * w // 4 + 3, y + 62],
          180, 360, fill=INK, width=3)
    d.line([(x + 6, deck_y), (x + w - 6, deck_y)], fill=INK, width=4)
    for fx in range(x + 14, x + w - 10, 14):
        d.line([(fx, deck_y - 14), (fx, deck_y)], fill=INK, width=1)
    d.line([(x + 6, y + h - 22), (x + w - 6, y + h - 22)], fill=WHITE,
           width=3)


def art_film(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(238, 226, 214))
    cx, cy = x + w // 2, y + h // 2
    for by in (cy - 30, cy + 22):
        d.rectangle([cx - 40, by, cx + 40, by + 8], fill=(40, 40, 48))
        for px in range(cx - 36, cx + 34, 10):
            d.rectangle([px, by + 2, px + 5, by + 6],
                        fill=(238, 226, 214))
    d.rectangle([cx - 32, cy - 18, cx + 32, cy + 20], fill=(60, 60, 70))
    disc(d, cx, cy, 13, (140, 180, 220), outline=WHITE, width=3)
    d.polygon([(cx - 3, cy - 6), (cx - 3, cy + 6), (cx + 6, cy)],
              fill=WHITE)
    d.polygon([(cx + 32, cy - 10), (cx + 44, cy - 4), (cx + 32, cy + 2)],
              fill=(60, 60, 70))


def art_snooker(d, x, y, w, h):
    d.rectangle([x, y, x + w, y + h], fill=(30, 60, 40))
    # the table, cushions and pockets
    d.rectangle([x + 8, y + 14, x + w - 8, y + h - 14], fill=(40, 110, 60),
                outline=(120, 84, 40), width=4)
    for px, py in ((x + 8, y + 14), (x + w // 2, y + 14),
                   (x + w - 8, y + 14), (x + 8, y + h - 14),
                   (x + w // 2, y + h - 14), (x + w - 8, y + h - 14)):
        disc(d, px, py, 5, (10, 10, 12))
    # the balls: a red triangle, the cue ball and the black
    for i, (bx, by) in enumerate(((62, 42), (70, 42), (54, 50), (62, 50),
                                  (70, 50), (58, 58), (66, 58))):
        disc(d, x + bx - 8 + (i % 2) * 2, y + by, 4, (200, 50, 40))
    disc(d, x + 30, y + h // 2, 5, WHITE, outline=INK, width=1)
    disc(d, x + w - 24, y + h - 28, 5, (20, 20, 24), outline=WHITE, width=1)
    # the cue, aimed at the white
    d.line([(x + 12, y + h - 20), (x + 28, y + h // 2 + 2)],
           fill=(210, 180, 120), width=3)


ART = {
    "fire": art_fire, "podium": art_podium, "factory": art_factory,
    "gold": art_gold, "database": art_database, "card": art_card,
    "car": art_car, "chart": art_chart, "climate": art_climate,
    "bridge": art_bridge, "film": art_film, "snooker": art_snooker,
}


def draw_art(img, kind, x, y, w, h):
    """Draw a pictogram at any size: render on a 100x100 tile, scale,
    then lay a soft top light and foot shade over it so the flat
    pictograms sit under the same light as the lead scenes."""
    tile = Image.new("RGB", (100, 100), PAPER)
    td = ImageDraw.Draw(tile)
    ART[kind](td, 0, 0, 100, 100)
    tile = tile.resize((w, h), Image.LANCZOS)
    img.paste(tile, (x, y))
    light = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(light)
    for j in range(h):
        t = j / max(h - 1, 1)
        ld.line([(0, j), (w, j)], fill=(255, 255, 255, int(30 * (1 - t))))
    img.paste(light, (x, y), light)
    shade = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for j in range(h):
        t = j / max(h - 1, 1)
        sd.line([(0, j), (w, j)], fill=(20, 16, 8, int(22 * t)))
    img.paste(shade, (x, y), shade)


# --- panels, strips and boxes -------------------------------------------------

LEAD_ART_H = 190


def lead_panel(img, d, box, num, art, headline, deck, src):
    x0, y0, x1, y1 = box
    frame(d, box)
    ax0, ay0, ax1 = x0 + 2, y0 + 2, x1 - 2
    SCENES[art](d, ax0, ay0, ax1 - ax0, LEAD_ART_H)
    d.line([(x0 + 2, y0 + LEAD_ART_H + 2), (x1 - 2, y0 + LEAD_ART_H + 2)],
           fill=EDGE, width=2)
    badge(d, x0 + 15, y0 + 15, num, r=12)
    y = para(d, x0 + 9, y0 + LEAD_ART_H + 9, headline, ft(SANSB, 19),
             x1 - x0 - 18, 21.5, max_lines=3)
    para(d, x0 + 9, y + 2, deck, ft(SANS, 11), x1 - x0 - 18, 13.5,
         max_lines=3)
    d.text((x0 + 9, y1 - 14), src, font=ft(SANSB, 8), fill=MUTED)


def feature_panel(img, d, box, num, art, headline, src):
    """An illustrated panel: a little scene at native 96x96, a bold
    headline beside it, the source tag along the bottom."""
    x0, y0, x1, y1 = box
    frame(d, box)
    ix, iy = x0 + 4, y0 + 4
    draw_art(img, art, ix, iy, 96, 96)
    d.rectangle([ix, iy, ix + 96, iy + 96], outline=EDGE, width=1)
    badge(d, x0 + 13, y0 + 13, num, r=9)
    tx = x0 + 106
    para(d, tx, y0 + 6, headline, ft(SANSB, 13.5), x1 - tx - 5, 16.5,
         max_lines=5)
    d.text((tx, y1 - 13), src, font=ft(SANSB, 8), fill=MUTED)


def stats_strip(d, box, stats):
    """Key-numbers strip: big verified figures, small labels, cells."""
    x0, y0, x1, y1 = box
    d.rectangle([x0, y0, x1, y1], fill=PANEL, outline=EDGE, width=1)
    n = len(stats)
    cw = (x1 - x0) / n
    nf = ft(SANSB, 15)
    lf = ft(SANS, 8)
    for i, (num, label) in enumerate(stats):
        cx = x0 + i * cw
        if i:
            d.line([(cx, y0 + 4), (cx, y1 - 4)], fill=EDGE, width=1)
        d.text((cx + (cw - tw(d, num, nf)) / 2, y0 + 1), num, font=nf,
               fill=RED)
        d.text((cx + (cw - tw(d, label, lf)) / 2, y0 + 18), label,
               font=lf, fill=MUTED)


def date_check(d, box, text):
    """Red-bordered DATE CHECK box: bold red label, body wrapped."""
    x0, y0, x1, y1 = box
    d.rectangle([x0, y0, x1, y1], outline=RED, width=2)
    lab = "DATE CHECK — "
    lfn = ft(SANSB, 9)
    bfn = ft(SANS, 9)
    labw = tw(d, lab, lfn)
    maxw = x1 - x0 - 16
    words = text.split()
    lines = []
    cur = ""
    limit = maxw - labw
    for word in words:
        trial = word if not cur else cur + " " + word
        if tw(d, trial, bfn) <= limit:
            cur = trial
        else:
            lines.append(cur)
            cur = word
            limit = maxw
    if cur:
        lines.append(cur)
    d.text((x0 + 8, y0 + 5), lab, font=lfn, fill=RED)
    yy = y0 + 5
    for i, ln in enumerate(lines):
        xx = x0 + 8 + labw if i == 0 else x0 + 8
        d.text((xx, yy), ln, font=bfn, fill=INK)
        yy += 12
    return yy


# --- story data -----------------------------------------------------------------
# Regions: EU Europe, ME Middle East, AP Asia-Pacific, AM Americas,
#          AF Africa, GL Global. The regions bar is computed from this list.

LEADS = [
    ("market",
     "Asia shares slide again as the AI rout rolls into Monday",
     "Taiex down 6%+, Kospi -3.8%, MSCI Asia -2.2% — but US futures "
     "bounce as Nasdaq 100 gains 2%.",
     "(Reuters · Bloomberg)", "AP"),
    ("summit",
     "Nepal's PM meets Modi in Delhi on first trip abroad",
     "Shah's first bilateral visit since March: talks on energy, trade "
     "and connectivity, then a joint press conference.",
     "(IANS · MEA)", "AP"),
    ("tanker",
     "Russia starts towing drone-hit ship Sparta II",
     "Blaze still burning off Finland; crew evacuated. Helsinki says "
     "the war is 'spilling over'.",
     "(Reuters · Euronews)", "EU"),
]

PANELS = [
    ("fire", "Indonesia factory fire: toll climbs as search goes on",
     "(Reuters · Euronews)", "AP"),
    ("podium", "South Korea's education minister quits over AI cheating scandal",
     "(Observer Voice)", "AP"),
    ("factory", "Japan's economy shrinks for first time in a year",
     "(Bloomberg)", "AP"),
    ("gold", "Hong Kong drugmaker Akeso plunges after US rejection",
     "(Bloomberg)", "AP"),
    ("database", "FBI probes apparent hack of its crime database",
     "(BBC · CNN)", "AM"),
    ("card", "Trump to work with Democrats on 10% card-interest cap",
     "(AP)", "AM"),
    ("car", "Toyota, Lexus recall 300,000+ cars over Takata airbags",
     "(AP)", "AM"),
    ("chart", "Asia's regulators move to steady the markets",
     "(Reuters)", "AP"),
    ("climate", "COP31 fallout: Guterres 'deeply disappointed'",
     "(Reuters)", "GL"),
    ("bridge", "Shah launches big infrastructure push in Arunachal",
     "(Jagran)", "AP"),
    ("film", "IFFI 2026 hosts BRICS roundtable on film ties",
     "(Jagran)", "AP"),
    ("snooker", "Anupama defends world women's snooker title",
     "(Jagran)", "AP"),
]

INDEX = [
    ("Saudi-led coalition intercepts Houthi missile", "(Daily Jagran)", "ME"),
    ("India, Bulgaria discuss IMEC and Black Sea ties", "(Daily Jagran)", "EU"),
    ("Nvidia chip-diversion row: fresh details on Alice Huang", "(Daily Jagran)", "AM"),
    ("Rajya Sabha MP Ramrao Wadkute dies in Delhi", "(Jagran)", "AP"),
    ("Nine pilgrims killed as vehicle rams truck in Kota", "(Jagran)", "AP"),
    ("Hyderabad students protest over alleged casteist remarks", "(Jagran)", "AP"),
    ("Kashmir saffron fields used as dumping ground, Mufti says", "(Jagran)", "AP"),
    ("Six sent to juvenile home after Mumbai assault", "(Jagran)", "AP"),
    ("JEE Main 2027 registration closes today", "(Jagran)", "AP"),
    ("Trump floats steep tax on firms building data centres abroad", "(AP)", "AM"),
    ("US loses measles-free status as virus spreads", "(AP)", "AM"),
    ("India need eight wickets on final day in Wellington", "(Khel Now)", "AP"),
    ("World chess championship: geniuses who wielded their magic", "(Jagran)", "GL"),
    ("Japan markets shut for holiday; futures point lower", "(Reuters)", "AP"),
    ("New World Development slides on discounted rights issue", "(Bloomberg)", "AP"),
    ("Democrats projected to win 258 House seats, biggest since 1992 (Sun)", "(DailyDrop)", "AM"),
    ("Verstappen wins chaotic Las Vegas Grand Prix (Sun)", "(Reflecto)", "GL"),
    ("Miley Cyrus marries Maxx Morando in California (Sun)", "(Reflecto)", "AM"),
    ("BepiColombo enters Mercury orbit after eight-year trip (Sun)", "(Euronews)", "GL"),
    ("Magnitude 6.8 quake off Timor-Leste; no tsunami threat (Sat)", "(Reflecto)", "AP"),
    ("Zelenskyy's 20-point peace plan: what it proposes (weekend)", "(Reflecto)", "EU"),
    ("Thousands march in Lisbon as living costs fuel anger (weekend)", "(Jagran)", "EU"),
    ("Myanmar's army-backed government calls ASEAN decision 'unfair'", "(Jagran)", "AF"),
    ("Mets agree $95m, eight-year deal with A.J. Ewing (Sun)", "(AP)", "AM"),
    ("TCU fires Sonny Dykes four years after title-game run (Sun)", "(AP)", "AM"),
]

# Key numbers for the strip under the masthead — each verified in SOURCES.md.
STATS = [
    ("6%+", "Taiex fall Monday"),
    ("2%", "Nasdaq futures bounce"),
    ("300k+", "cars in Toyota recall"),
    ("10%", "card-interest cap floated"),
    ("32%", "Akeso shares fall"),
    ("34", "Nepal delegation members"),
]

REGION_ORDER = [("EU", "EUROPE"), ("ME", "MIDDLE EAST"), ("AP", "ASIA-PACIFIC"),
                ("AM", "AMERICAS"), ("AF", "AFRICA"), ("GL", "GLOBAL")]

DATE_CHECK_TEXT = (
    "Every story here was reported or still developing on Monday 23 Nov "
    "2026 — wires read through Monday morning (WIB); weekend results "
    "carried as weekend results, as a Monday paper does. Left out as "
    "other days' news: COP31's collapse, the Kyiv strike and India's 720 "
    "(all 22 Nov); the Sparta II hit, 'Chapo Isidro' and the Hormuz "
    "tankers (20–21 Nov); GTA VI's release (19 Nov)."
)


def regions_bar():
    counts = {}
    for story in LEADS + PANELS + INDEX:
        counts[story[-1]] = counts.get(story[-1], 0) + 1
    return "  ·  ".join(f"{name} {counts.get(code, 0)}"
                         for code, name in REGION_ORDER)


def flow_columns(d, items, first_num, font, colw, ncols):
    """Wrap numbered, source-tagged items into balanced columns,
    reading down column 1, then column 2, and so on."""
    entries = [wrap_tagged(d, f"{first_num + j}. {text}", tag, font, colw)
               for j, (text, tag, _region) in enumerate(items)]
    total = sum(len(e) for e in entries)
    cols = [[] for _ in range(ncols)]
    counts = [0] * ncols
    ci = 0
    for e in entries:
        if ci < ncols - 1 and counts[ci] > 0 and counts[ci] >= total / ncols:
            ci += 1
        cols[ci].append(e)
        counts[ci] += len(e)
    return cols


def draw_flow(d, cols, x0, y, colw, gap, font, leading, item_gap=1.0):
    bottom = y
    for ci, col in enumerate(cols):
        x = x0 + ci * (colw + gap)
        yy = y
        for lines in col:
            for ln, tag_start in lines:
                if tag_start < 0:
                    d.text((x, yy), ln, font=font, fill=INK)
                elif tag_start == 0:
                    d.text((x, yy), ln, font=font, fill=MUTED)
                else:
                    d.text((x, yy), ln[:tag_start], font=font, fill=INK)
                    d.text((x + tw(d, ln[:tag_start], font), yy),
                           ln[tag_start:], font=font, fill=MUTED)
                yy += leading
            yy += item_gap
        bottom = max(bottom, yy - item_gap)
    return bottom


def build():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    total = len(LEADS) + len(PANELS) + len(INDEX)

    # masthead
    title = "The Daily Compass"
    tf = ft(SERIF, 38)
    d.text(((W - tw(d, title, tf)) / 2, 0), title, font=tf, fill=INK)
    hrule(d, M, 44, W - M, 3)
    d.text((M, 49), "Monday 23 November 2026",
           font=ft(SANSB, 12), fill=INK)
    right = f"{total} verified stories — reported Monday 23 Nov 2026"
    d.text((W - M - tw(d, right, ft(SANS, 11)), 50), right,
           font=ft(SANS, 11), fill=MUTED)
    hrule(d, M, 66, W - M, 2)

    # key-numbers strip
    stats_strip(d, (M, 70, W - M, 98), STATS)

    # lead row: 3 art-first cards, scenes 190 tall, bold 19pt headlines
    top = 102
    lw = (W - 2 * M - 2 * 10) // 3
    lh = 320
    for i, (art, head, deck, src, _region) in enumerate(LEADS):
        x0 = M + i * (lw + 10)
        lead_panel(img, d, (x0, top, x0 + lw, top + lh), i + 1, art, head,
                   deck, src)

    # illustrated panels: 4 x 3 grid of native-size scenes, stories 4-15
    py = top + lh + 6
    pw = (W - 2 * M - 3 * 8) // 4
    ph = 104
    for r in range(3):
        for c in range(4):
            i = r * 4 + c
            art, head, src, _region = PANELS[i]
            x0 = M + c * (pw + 8)
            y0 = py + r * (ph + 6)
            feature_panel(img, d, (x0, y0, x0 + pw, y0 + ph), i + 4, art,
                          head, src)
    pbot = py + 3 * ph + 2 * 6

    # index header, with the computed regions bar on the same line
    iy = pbot + 8
    last = len(LEADS) + len(PANELS)
    d.text((M, iy), f"ALSO TODAY — INDEX {last + 1}–{total}",
           font=ft(SANSB, 12.5), fill=INK)
    bar = regions_bar()
    bfn_bar = ft(SANSB, 9.5)
    d.text((W - M - tw(d, bar, bfn_bar), iy + 2), bar,
           font=bfn_bar, fill=MUTED)
    hrule(d, M, iy + 18, W - M, 2)

    # index: four balanced columns at a readable 10.5pt
    ifn = ft(SANS, 10.5)
    icolw = (W - 2 * M - 3 * 12) // 4
    icols = flow_columns(d, INDEX, last + 1, ifn, icolw, 4)
    ibot = draw_flow(d, icols, M, iy + 24, icolw, 12, ifn, 12.6,
                     item_gap=1.0)

    # date check box
    cby = ibot + 8
    date_check(d, (M, cby, W - M, cby + 29), DATE_CHECK_TEXT)

    # footer
    d.text((M, cby + 34),
           "Every story dated & sourced — checked Monday 23 Nov 2026. "
           f"Full source list on file for all {total} stories; claims are "
           "labelled as claims; market figures are Monday's moves. "
           "All pictures drawn in code.",
           font=ft(SANS, 8), fill=MUTED)

    if os.environ.get("RENDER_DEBUG"):
        print(f"panels_bottom={pbot:.0f} index_bottom={ibot:.0f} "
              f"datebox_bottom={cby + 29:.0f} footer_y={cby + 34:.0f} "
              f"stories={total} regions={regions_bar()}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, format="PNG", optimize=True)
    print(OUT)


if __name__ == "__main__":
    build()
