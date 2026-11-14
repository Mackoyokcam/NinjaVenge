"""Compose the two territory backdrops (static part: sky, scenery, lanes, ground).

Sources (all CC0, unzip each first):
    Kenney "Background Elements Redux"   https://opengameart.org/content/background-elements-redux
    Tio Aimar "2D Platformer Jungle Pack"  https://opengameart.org/content/2d-platformer-jungle-pack

Usage:
    python tools/prepare_backgrounds.py <Background Elements Redux dir> <Jungle Pack dir>

Writes src/data/bg/medieval.png and src/data/bg/prehistoric.png (screen sized).
Animated bits (torch flames, clouds, volcano smoke) are drawn at runtime by ui.Background.
"""
import math
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

from ninjavenge import config as C  # noqa: E402
from ninjavenge.ui import VOLCANO_CRATER, torch_spots  # noqa: E402

W, H = C.SCREEN_W, C.SCREEN_H
GROUND = C.LANE_FLOORS[0]
OUT = os.path.join(C.DATA_DIR, "bg")


def load(path):
    return pygame.image.load(path).convert_alpha()


def scaled(img, k):
    w, h = img.get_size()
    return pygame.transform.smoothscale(img, (max(1, round(w * k)), max(1, round(h * k))))


def recolor(img, color):
    """Flat silhouette in `color`, keeping the image's alpha."""
    out = img.copy()
    out.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
    out.fill((*color, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return out


def gradient(surf, stops, y0=0, y1=H):
    """Vertical gradient through (t, color) stops."""
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0 - 1)
        for (ta, ca), (tb, cb) in zip(stops, stops[1:]):
            if ta <= t <= tb:
                k = (t - ta) / max(1e-6, tb - ta)
                col = [round(ca[i] + (cb[i] - ca[i]) * k) for i in range(3)]
                break
        pygame.draw.line(surf, col, (0, y), (W, y))


def tile_row(surf, tile, y, x0=0):
    x = x0
    while x < W:
        surf.blit(tile, (x, y))
        x += tile.get_width()


# ---------------------------------------------------------------- medieval
def medieval(kenney):
    rng = random.Random(11)
    bg = os.path.join(kenney, "Backgrounds")
    png = os.path.join(kenney, "PNG", "Default")
    s = pygame.Surface((W, H)).convert()
    gradient(s, [(0.0, (16, 14, 40)), (0.45, (58, 34, 78)), (0.72, (170, 84, 92)), (0.86, (236, 140, 92)), (1.0, (236, 140, 92))])
    for _ in range(110):
        x, y = rng.randrange(W), rng.randrange(0, 300)
        b = rng.randrange(120, 230)
        s.set_at((x, y), (b, b, b))
    moon = scaled(load(os.path.join(png, "moonFull.png")), 1.6)
    moon.fill((255, 236, 210, 255), special_flags=pygame.BLEND_RGBA_MULT)
    s.blit(moon, moon.get_rect(center=(1210, 135)))

    # far mountains
    mountains = scaled(load(os.path.join(bg, "Elements", "mountains.png")), 1.5)
    mountains = recolor(mountains, (104, 56, 92))
    for x in (-200, mountains.get_width() - 260):
        s.blit(mountains, (x, 640 - mountains.get_height() + 60))

    # the knight's castle: a hazy far keep, then the main castle in silhouette
    _castle(s, 1150, 640, 0.7, (92, 50, 92), rng, windows=6)
    _castle(s, 520, 690, 1.25, (40, 24, 56), rng, windows=26)

    # a low line of pines in front of the walls
    pine = load(os.path.join(png, "treePine.png"))
    for i in range(30):
        k = rng.uniform(0.45, 0.75)
        tree = recolor(scaled(pine, k), (24, 15, 34))
        x = i * 52 + rng.randrange(-20, 20)
        s.blit(tree, (x, GROUND + 4 - tree.get_height()))

    # cobblestone courtyard
    pygame.draw.rect(s, (44, 38, 54), (0, GROUND, W, H - GROUND))
    for row, y in enumerate(range(GROUND + 10, H + 20, 22)):
        x = -rng.randrange(0, 30) - (row % 2) * 18
        while x < W:
            w = rng.randrange(30, 46)
            shade = rng.randrange(58, 78)
            pygame.draw.ellipse(s, (shade, shade - 6, shade + 10), (x, y, w, 18))
            x += w + 4

    # stone ramparts as lanes
    for floor in C.LANE_FLOORS:
        _rampart(s, floor, floor == GROUND, rng)
    for x, y in torch_spots():
        _torch_bracket(s, x, y)
    return s


def _castle(s, cx, base, k, color, rng, windows):
    """Keep with crenellated walls and round towers with pointed roofs."""
    def merlons(x0, x1, top, size):
        x = x0
        while x + size <= x1:
            pygame.draw.rect(s, color, (x, top - size, size, size))
            x += size * 2

    m = round(14 * k)
    wall_top = base - round(200 * k)
    pygame.draw.rect(s, color, (cx - round(300 * k), wall_top, round(600 * k), base - wall_top))
    merlons(cx - round(300 * k), cx + round(300 * k), wall_top, m)
    keep_w, keep_top = round(170 * k), base - round(330 * k)
    pygame.draw.rect(s, color, (cx - keep_w // 2, keep_top, keep_w, base - keep_top))
    merlons(cx - keep_w // 2, cx + keep_w // 2, keep_top, m)
    lit = []
    for tx, w, h in ((-300, 80, 290), (300, 80, 290), (-150, 64, 250), (150, 64, 250), (0, 56, 420)):
        tx, w, h = cx + round(tx * k), round(w * k), round(h * k)
        top = base - h
        pygame.draw.rect(s, color, (tx - w // 2, top, w, h))
        pygame.draw.polygon(s, color, [(tx - w // 2 - round(8 * k), top), (tx + w // 2 + round(8 * k), top),
                                       (tx, top - round(w * 1.3))])
        pygame.draw.line(s, color, (tx, top - round(w * 1.3)), (tx, top - round(w * 1.3) - round(26 * k)), 2)
        pygame.draw.polygon(s, color, [(tx, top - round(w * 1.3) - round(26 * k)),
                                       (tx + round(22 * k), top - round(w * 1.3) - round(20 * k)),
                                       (tx, top - round(w * 1.3) - round(14 * k))])
        lit.append((tx - w // 2 + 6, top + 10, w - 12, h - 30))
    lit.append((cx - keep_w // 2 + 10, keep_top + 20, keep_w - 20, base - keep_top - 60))
    gate_w = round(70 * k)
    pygame.draw.rect(s, (14, 8, 20), (cx - gate_w // 2, base - round(80 * k), gate_w, round(80 * k)))
    pygame.draw.ellipse(s, (14, 8, 20), (cx - gate_w // 2, base - round(80 * k) - gate_w // 2, gate_w, gate_w))
    for _ in range(windows):
        x, y, w, h = rng.choice(lit)
        wx, wy = x + rng.randrange(max(1, w)), y + rng.randrange(max(1, h))
        ww, wh = max(3, round(6 * k)), max(5, round(11 * k))
        glow = (255, 196, 96) if k > 1 else (220, 140, 110)
        pygame.draw.rect(s, glow, (wx - ww // 2, wy - wh // 2, ww, wh), border_top_left_radius=ww // 2,
                         border_top_right_radius=ww // 2)


def _rampart(s, floor, ground_lane, rng):
    t = C.LANE_THICKNESS + 8
    if not ground_lane:
        for x in range(60, W, 300):   # stone corbels holding the walkway
            pygame.draw.polygon(s, (60, 54, 72), [(x - 16, floor + t), (x + 16, floor + t), (x + 8, floor + t + 26),
                                                  (x - 8, floor + t + 26)])
        for x in range(210, W - 100, 600):   # the knight's red banners
            pygame.draw.rect(s, (150, 24, 32), (x - 16, floor + t, 32, 58))
            pygame.draw.polygon(s, (150, 24, 32), [(x - 16, floor + t + 58), (x + 16, floor + t + 58), (x, floor + t + 72)])
            pygame.draw.rect(s, (230, 180, 70), (x - 16, floor + t, 32, 4))
            pygame.draw.circle(s, (230, 180, 70), (x, floor + t + 28), 7, 2)
        pygame.draw.rect(s, (0, 0, 0), (0, floor + t, W, 3))
    pygame.draw.rect(s, (104, 98, 116), (0, floor, W, t))
    pygame.draw.line(s, (170, 160, 180), (0, floor), (W, floor), 2)
    off = rng.randrange(0, 40)
    for x in range(-off, W, 56):
        pygame.draw.line(s, (70, 64, 84), (x, floor + 3), (x, floor + t - 1), 2)
    pygame.draw.line(s, (70, 64, 84), (0, floor + t // 2 + 1), (W, floor + t // 2 + 1), 1)


def _torch_bracket(s, x, y):
    pygame.draw.line(s, (40, 30, 26), (x, y + 60), (x, y + 8), 4)
    pygame.draw.polygon(s, (70, 60, 56), [(x - 8, y + 6), (x + 8, y + 6), (x + 4, y + 16), (x - 4, y + 16)])


# ---------------------------------------------------------------- prehistoric
def prehistoric(jungle):
    rng = random.Random(23)
    png = os.path.join(jungle, "PNG")
    layers = os.path.join(png, "bg_jungle_layers")
    s = pygame.Surface((W, H)).convert()
    gradient(s, [(0.0, (92, 48, 66)), (0.35, (196, 92, 70)), (0.62, (246, 170, 100)), (1.0, (250, 206, 140))])

    # the volcano, glowing crater and lava streaks
    cx, cy = VOLCANO_CRATER
    pygame.draw.polygon(s, (96, 58, 66), [(cx - 620, 700), (cx - 80, cy + 6), (cx + 80, cy + 6), (cx + 660, 700)])
    pygame.draw.polygon(s, (78, 46, 58), [(cx + 10, cy + 6), (cx + 80, cy + 6), (cx + 660, 700), (cx + 180, 700)])
    pygame.draw.ellipse(s, (255, 120, 40), (cx - 62, cy - 4, 124, 18))
    pygame.draw.ellipse(s, (255, 200, 90), (cx - 40, cy, 80, 9))
    for sx, length, sway in ((-30, 170, -40), (8, 230, 24), (40, 120, 60)):
        pts = [(cx + sx + sway * math.sin(k / 6) * (k / 12), cy + 8 + k * length / 12) for k in range(13)]
        pygame.draw.lines(s, (240, 100, 40), False, pts, 5)
        pygame.draw.lines(s, (255, 190, 80), False, pts, 2)

    # Tio Aimar's jungle hills, warmed to match the sky (back to front)
    k = W / 1280
    for name, tint, bottom in (("bg5_e", (236, 176, 150), 720), ("bg5_d", (220, 160, 140), 730),
                               ("bg5_c", (230, 220, 190), 760), ("bg5_b", (220, 220, 200), 790)):
        layer = scaled(load(os.path.join(layers, f"{name}.png")), k)
        layer.fill((*tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
        s.blit(layer, (0, bottom - layer.get_height()))

    # jungle trees and ferns behind the lanes
    trees = [load(os.path.join(png, f"jungle_pack_{n}.png")) for n in (57, 59)]
    plants = [load(os.path.join(png, f"jungle_pack_{n}.png")) for n in (66, 63, 64, 68)]
    for floor in C.LANE_FLOORS:
        x = rng.randrange(-60, 120)
        while x < W:
            if floor == GROUND or rng.random() < 0.45:
                img = rng.choice(trees if floor == GROUND else plants)
                img = scaled(img, rng.uniform(1.0, 1.4) if floor == GROUND else rng.uniform(0.6, 0.85))
                img = img.copy()
                img.fill((150, 150, 150, 255), special_flags=pygame.BLEND_RGBA_MULT)   # keep them in the background
                r = img.get_bounding_rect()
                s.blit(img, (x, floor + 4 - r.bottom))
            x += rng.randrange(160, 300)

    # ground and grassy rock ledges as lanes
    ground = scaled(load(os.path.join(png, "jungle_pack_05.png")), 0.8)
    tile_row(s, ground, GROUND - 6)
    tile_row(s, ground, GROUND - 6 + ground.get_height())
    ledge = scaled(load(os.path.join(png, "jungle_pack_15.png")), 0.5)
    for floor in C.LANE_FLOORS[1:]:
        tile_row(s, ledge, floor - 5, x0=-rng.randrange(0, 60))
    for x, y in torch_spots():
        _tiki(s, x, y)
    return s


def _tiki(s, x, y):
    pygame.draw.line(s, (70, 44, 30), (x, y + 62), (x, y + 10), 5)
    for k in range(3):
        pygame.draw.line(s, (130, 90, 50), (x - 4, y + 22 + k * 10), (x + 4, y + 18 + k * 10), 2)
    pygame.draw.polygon(s, (90, 60, 40), [(x - 8, y + 6), (x + 8, y + 6), (x + 5, y + 16), (x - 5, y + 16)])


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    pygame.init()
    pygame.display.set_mode((1, 1))
    os.makedirs(OUT, exist_ok=True)
    pygame.image.save(medieval(sys.argv[1]), os.path.join(OUT, "medieval.png"))
    pygame.image.save(prehistoric(sys.argv[2]), os.path.join(OUT, "prehistoric.png"))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
