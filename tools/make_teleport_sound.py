"""Synthesize the Shinobi Mode teleport sound (src/data/teleport.wav).

A short "vwip-vwip": two fast rising pitch sweeps with a breath of noise,
like a fighter blinking out of sight. Made from scratch, so no license strings.

Usage:
    python tools/make_teleport_sound.py
"""
import math
import os
import random
import struct
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "src", "data", "teleport.wav")
RATE = 44100


def sweep(duration, f0, f1, volume):
    """Exponential pitch sweep with a sharp attack and quick decay."""
    out, phase = [], 0.0
    n = int(duration * RATE)
    for i in range(n):
        t = i / n
        freq = f0 * (f1 / f0) ** t
        phase += 2 * math.pi * freq / RATE
        tone = math.sin(phase) + 0.35 * math.sin(2 * phase) + 0.15 * math.sin(3 * phase + 0.5)
        env = min(1.0, t / 0.08) * (1 - t) ** 1.6
        out.append(volume * env * tone)
    return out


def noise(duration, volume, rng):
    out, prev = [], 0.0
    n = int(duration * RATE)
    for i in range(n):
        t = i / n
        x = rng.uniform(-1, 1)
        hp = x - prev            # crude high-pass: airy, not rumbly
        prev = x
        out.append(volume * hp * (1 - t) ** 2 * min(1.0, t / 0.05))
    return out


def mix(dest, src, at):
    start = int(at * RATE)
    need = start + len(src)
    if len(dest) < need:
        dest.extend([0.0] * (need - len(dest)))
    for i, v in enumerate(src):
        dest[start + i] += v


def main():
    rng = random.Random(3)
    samples = []
    mix(samples, sweep(0.085, 380, 2600, 0.45), 0.0)
    mix(samples, noise(0.09, 0.25, rng), 0.0)
    mix(samples, sweep(0.11, 520, 3400, 0.35), 0.085)
    mix(samples, noise(0.1, 0.18, rng), 0.085)
    peak = max(abs(v) for v in samples)
    with wave.open(OUT, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(v / peak * 0.8 * 32767)) for v in samples))
    print("wrote", OUT, f"{len(samples) / RATE:.2f}s")


if __name__ == "__main__":
    main()
