"""Convert pzUH's CC0 GameArt2D packs into game-ready boss frames.

Sources (CC0, by pzUH, https://opengameart.org):
    The Knight - Free Sprite  https://opengameart.org/content/the-knight-free-sprite   (FreeKnight.zip)
    Free Dino Sprites         https://opengameart.org/content/free-dino-sprites        (FreeDinoSprite.zip)
    Ninja Girl - Free Sprite  https://opengameart.org/content/ninja-girl-free-sprite   (NinjaGirl.zip)

Usage (unzip each pack first):
    python tools/prepare_boss_art.py <FreeKnight/png dir> <FreeDinoSprite/png dir> <NinjaGirl/png dir>

Each animation is scaled to the target height, cropped to the union of its frames, and
padded so the body's centre (taken from the first frame) sits at the horizontal centre
of every frame, with the feet on the bottom edge. The game can then anchor every boss
frame at its centre regardless of how the source canvases were laid out.
"""
import os
import re
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "data", "boss")

# character -> (target body height in px, {output folder: source prefix})
JOBS = {
    "knight": (215, {"running": "Walk", "attack": "Attack", "dying": "Dead"}),
    "dino": (190, {"running": "Walk", "charge": "Run", "dying": "Dead"}),
    "kage": (160, {"running": "Run", "idle": "Idle", "throw": "Throw", "attack": "Attack",
                   "slide": "Slide", "dying": "Dead"}),
}


def frames_for(src, prefix):
    # "Walk (1).png" (knight, dino) or "Run__000.png" (ninja girl)
    pat = re.compile(rf"^{prefix}(?: \((\d+)\)|__(\d+))\.png$")
    names = sorted((int(m.group(1) or m.group(2)), n) for n in os.listdir(src) if (m := pat.match(n)))
    return [pygame.image.load(os.path.join(src, n)).convert_alpha() for _, n in names]


def union(rects):
    r = rects[0].copy()
    for o in rects[1:]:
        r.union_ip(o)
    return r


def process(name, src):
    height, anims = JOBS[name]
    walk = frames_for(src, anims["running"])
    scale = height / union([f.get_bounding_rect() for f in walk]).height
    for folder, prefix in anims.items():
        frames = frames_for(src, prefix)
        if not frames:
            raise SystemExit(f"no '{prefix}' frames in {src}")
        box = union([f.get_bounding_rect() for f in frames])
        ref_x = frames[0].get_bounding_rect().centerx
        half = max(ref_x - box.left, box.right - ref_x)
        out_dir = os.path.join(OUT, name, folder)
        os.makedirs(out_dir, exist_ok=True)
        for old in os.listdir(out_dir):
            os.remove(os.path.join(out_dir, old))
        for i, f in enumerate(frames, 1):
            canvas = pygame.Surface((half * 2, box.height), pygame.SRCALPHA)
            canvas.blit(f, (half - ref_x, -box.top))
            w, h = max(1, round(canvas.get_width() * scale)), max(1, round(canvas.get_height() * scale))
            pygame.image.save(pygame.transform.smoothscale(canvas, (w, h)),
                              os.path.join(out_dir, f"{folder}_{i:02d}.png"))
        print(f"{name}/{folder}: {len(frames)} frames -> {w}x{h}")


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    pygame.init()
    pygame.display.set_mode((1, 1))
    process("knight", sys.argv[1])
    process("dino", sys.argv[2])
    process("kage", sys.argv[3])


if __name__ == "__main__":
    main()
