"""Build the knight, pumpkin and dinosaur death sounds from CC0 source recordings.

    knight_dead.wav   groan, then armor and chainmail clattering to the ground
    pumpkin_dead.wav  a pumpkin smashing, with a ghostly sigh as the spirit leaves
    dino_dead.wav     a dying roar
    kage_dead.wav     a last breath, then her blade clattering to the ground

Sources (all CC0, see CREDITS):
    <rpg>       artisticdude "RPG Sound Pack"   (folder "RPG Sound Pack")
    <pumpkin>   tinyworlds "break pumpkin"      (folder with pumpkin_break_01_0.ogg)
    <creature>  rubberduck "80 CC0 creature SFX" (folder with roar_01.ogg)

Usage:
    python tools/make_death_sounds.py <rpg> <pumpkin> <creature>
"""
import array
import os
import sys
import wave

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "src", "data")
RATE = 44100


def load(path):
    """Decode any format pygame reads into mono floats in -1..1 at RATE."""
    raw = array.array("h", pygame.mixer.Sound(path).get_raw())
    return [(raw[i] + raw[i + 1]) / 65536 for i in range(0, len(raw) - 1, 2)]


def mix(layers):
    """layers: (samples, start_seconds, gain). Normalized to 0.85 peak."""
    out = []
    for samples, at, gain in layers:
        start = int(at * RATE)
        if len(out) < start + len(samples):
            out.extend([0.0] * (start + len(samples) - len(out)))
        for i, v in enumerate(samples):
            out[start + i] += v * gain
    peak = max(abs(v) for v in out) or 1.0
    return [v / peak * 0.85 for v in out]


def fade_tail(samples, seconds=0.08):
    n = min(len(samples), int(seconds * RATE))
    for i in range(n):
        samples[-1 - i] *= i / n
    return samples


def write(name, samples):
    path = os.path.join(DATA, name)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(array.array("h", (int(v * 32767) for v in fade_tail(samples))).tobytes())
    print("wrote", path, f"{len(samples) / RATE:.2f}s")


def main(rpg, pumpkin, creature):
    pygame.mixer.init(RATE, -16, 2)
    inv = os.path.join(rpg, "inventory")
    write("knight_dead.wav", mix([
        (load(os.path.join(rpg, "NPC", "giant", "giant2.wav")), 0.0, 1.0),     # groan
        (load(os.path.join(inv, "armor-light.wav")), 0.35, 0.8),               # knees buckle
        (load(os.path.join(inv, "chainmail2.wav")), 0.55, 0.9),                # collapses
        (load(os.path.join(inv, "metal-small3.wav")), 0.85, 0.7),              # helmet hits the ground
        (load(os.path.join(inv, "metal-small1.wav")), 1.05, 0.45),             # ...and rolls
    ]))
    write("pumpkin_dead.wav", mix([
        (load(os.path.join(pumpkin, "pumpkin_break_01_0.ogg")), 0.0, 1.0),
        (load(os.path.join(rpg, "NPC", "shade", "shade3.wav")), 0.12, 0.45),   # spirit sighs out
    ]))
    write("dino_dead.wav", mix([
        (load(os.path.join(creature, "roar_03.ogg")), 0.0, 1.0),     # bellow...
        (load(os.path.join(creature, "roar_02.ogg")), 0.3, 0.9),     # ...trailing off as he falls
    ]))
    write("kage_dead.wav", mix([
        (load(os.path.join(creature, "breath.ogg")), 0.0, 3.0),           # last breath (quiet source)
        (load(os.path.join(rpg, "NPC", "shade", "shade5.wav")), 0.05, 0.5),  # the shadow fades
        (load(os.path.join(inv, "metal-small3.wav")), 0.45, 0.8),         # blade hits the ground
        (load(os.path.join(inv, "metal-small1.wav")), 0.62, 0.4),
    ]))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
