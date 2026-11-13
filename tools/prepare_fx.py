"""Copy and resize the smoke-bomb effect assets used by Shinobi Mode.

Sources:
    Kenney "Smoke Particles" (CC0)   https://opengameart.org/content/smoke-particle-assets  (smokeParticleAssets.zip)
    dklon "Poof Noises" (CC-BY 3.0)   https://opengameart.org/content/poof-noises            (poofs.zip)

Usage (unzip both first):
    python tools/prepare_fx.py <smokeParticleAssets/PNG dir> <poofs dir>
"""
import os
import shutil
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "data")
PUFFS = [0, 3, 6, 9, 12, 15, 18, 21]   # a varied subset of the 25 white puffs
PUFF_SIZE = 120
FLASH_SIZE = 150


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    png_dir, sound_dir = sys.argv[1], sys.argv[2]
    pygame.init()
    pygame.display.set_mode((1, 1))
    out = os.path.join(DATA, "fx")
    os.makedirs(out, exist_ok=True)
    for i, n in enumerate(PUFFS):
        img = pygame.image.load(os.path.join(png_dir, "White puff", f"whitePuff{n:02d}.png")).convert_alpha()
        w, h = img.get_size()
        s = PUFF_SIZE / max(w, h)
        pygame.image.save(pygame.transform.smoothscale(img, (round(w * s), round(h * s))),
                          os.path.join(out, f"smoke_{i:02d}.png"))
    flash = pygame.image.load(os.path.join(png_dir, "Flash", "flash00.png")).convert_alpha()
    w, h = flash.get_size()
    s = FLASH_SIZE / max(w, h)
    pygame.image.save(pygame.transform.smoothscale(flash, (round(w * s), round(h * s))), os.path.join(out, "flash.png"))
    shutil.copyfile(os.path.join(sound_dir, "poof_1.wav"), os.path.join(DATA, "smoke_bomb.wav"))
    print(f"wrote {len(PUFFS)} puffs, flash.png and smoke_bomb.wav")


if __name__ == "__main__":
    main()
