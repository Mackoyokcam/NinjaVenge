"""Particles and floating text: cheap juice that makes hits feel good."""
import math
import random

import pygame

GRAVITY = 900


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "gravity")

    def __init__(self, x, y, vx, vy, life, color, size, gravity=True):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.color, self.size, self.gravity = color, size, gravity


class FloatText:
    __slots__ = ("x", "y", "surf", "life", "max_life")

    def __init__(self, x, y, surf, life):
        self.x, self.y, self.surf = x, y, surf
        self.life = self.max_life = life


class Effects:
    def __init__(self, font_factory):
        self.font = font_factory
        self.particles = []
        self.texts = []

    def burst(self, x, y, color, n=14, speed=320, size=4, life=0.5):
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            s = random.uniform(0.3, 1.0) * speed
            self.particles.append(Particle(x, y, math.cos(a) * s, math.sin(a) * s - 120,
                                           random.uniform(0.6, 1.0) * life, color, size))

    def sparks(self, x, y, color, n=8):
        self.burst(x, y, color, n=n, speed=420, size=3, life=0.25)

    def text(self, x, y, text, color, size=30, life=0.9):
        font = self.font(size)
        shadow = font.render(text, True, (0, 0, 0))
        fg = font.render(text, True, color)
        surf = pygame.Surface((fg.get_width() + 2, fg.get_height() + 2), pygame.SRCALPHA)
        surf.blit(shadow, (2, 2))
        surf.blit(fg, (0, 0))
        self.texts.append(FloatText(x, y, surf, life))

    def update(self, dt):
        for p in self.particles:
            p.life -= dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            if p.gravity:
                p.vy += GRAVITY * dt
        self.particles = [p for p in self.particles if p.life > 0]
        for t in self.texts:
            t.life -= dt
            t.y -= 60 * dt
        self.texts = [t for t in self.texts if t.life > 0]

    def draw(self, surf):
        for p in self.particles:
            r = max(1, round(p.size * p.life / p.max_life))
            pygame.draw.circle(surf, p.color, (round(p.x), round(p.y)), r)
        for t in self.texts:
            alpha = 255 * min(1.0, t.life / (t.max_life * 0.4))
            t.surf.set_alpha(int(alpha))
            surf.blit(t.surf, t.surf.get_rect(center=(round(t.x), round(t.y))))
