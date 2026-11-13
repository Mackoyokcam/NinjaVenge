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


class Puff:
    __slots__ = ("x", "y", "vx", "vy", "image", "life", "max_life", "start", "end", "delay")

    def __init__(self, x, y, vx, vy, image, life, start, end, delay=0.0):
        self.x, self.y, self.vx, self.vy, self.image = x, y, vx, vy, image
        self.life = self.max_life = life
        self.start, self.end, self.delay = start, end, delay


class Effects:
    def __init__(self, font_factory, assets=None):
        self.font = font_factory
        self.particles = []
        self.texts = []
        self.puffs = []
        self._smoke = self._flash = None
        if assets is not None:
            try:
                grey = []
                for i in range(8):
                    img = assets.image(f"fx/smoke_{i:02d}.png").copy()
                    img.fill((165, 160, 180), special_flags=pygame.BLEND_RGB_MULT)   # ninja-grey smoke
                    grey.append(img)
                self._smoke = grey
                self._flash = assets.image("fx/flash.png")
            except (FileNotFoundError, pygame.error):
                pass   # fall back to particle smoke

    def burst(self, x, y, color, n=14, speed=320, size=4, life=0.5):
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            s = random.uniform(0.3, 1.0) * speed
            self.particles.append(Particle(x, y, math.cos(a) * s, math.sin(a) * s - 120,
                                           random.uniform(0.6, 1.0) * life, color, size))

    def sparks(self, x, y, color, n=8):
        self.burst(x, y, color, n=n, speed=420, size=3, life=0.25)

    def smoke_bomb(self, x, y):
        """A smoke bomb going off: quick flash, then billowing grey puffs."""
        if not self._smoke:
            self.burst(x, y, (190, 190, 210), n=16, speed=180, size=7, life=0.35)
            return
        self.puffs.append(Puff(x, y, 0, 0, self._flash, 0.12, 0.4, 1.1))
        for i in range(12):
            a = random.uniform(0, 2 * math.pi)
            r = random.uniform(8, 30)
            img = random.choice(self._smoke)
            if random.random() < 0.5:
                img = pygame.transform.flip(img, True, False)
            self.puffs.append(Puff(x + math.cos(a) * r, y + math.sin(a) * r * 0.7,
                                   math.cos(a) * random.uniform(40, 110), math.sin(a) * 60 - random.uniform(20, 60),
                                   img, random.uniform(0.5, 0.8), random.uniform(0.3, 0.45),
                                   random.uniform(1.0, 1.45), delay=random.uniform(0, 0.05)))

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
        for p in self.puffs:
            if p.delay > 0:
                p.delay -= dt
                continue
            p.life -= dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vx *= 0.92
            p.vy *= 0.92
        self.puffs = [p for p in self.puffs if p.life > 0]

    def draw(self, surf):
        for p in self.puffs:
            if p.delay > 0:
                continue
            t = 1 - p.life / p.max_life                    # 0 -> 1 over the puff's life
            grow = 1 - (1 - t) ** 3                        # fast billow, slow settle
            scale = p.start + (p.end - p.start) * grow
            w, h = p.image.get_size()
            img = pygame.transform.smoothscale(p.image, (max(1, int(w * scale)), max(1, int(h * scale))))
            img.set_alpha(int(255 * (1 - t) ** 1.5))
            surf.blit(img, img.get_rect(center=(round(p.x), round(p.y))))
        self._draw_particles(surf)

    def _draw_particles(self, surf):
        for p in self.particles:
            r = max(1, round(p.size * p.life / p.max_life))
            pygame.draw.circle(surf, p.color, (round(p.x), round(p.y)), r)
        for t in self.texts:
            alpha = 255 * min(1.0, t.life / (t.max_life * 0.4))
            t.surf.set_alpha(int(alpha))
            surf.blit(t.surf, t.surf.get_rect(center=(round(t.x), round(t.y))))
