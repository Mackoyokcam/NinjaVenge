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


class Ghost:
    """A flickering, squashed copy of the ninja: 'out' shrinks to a line, 'in' grows from one."""
    __slots__ = ("image", "rect", "mode", "life", "max_life", "delay")

    def __init__(self, image, rect, mode, life, delay=0.0):
        self.image, self.rect, self.mode = image, rect, mode
        self.life = self.max_life = life
        self.delay = delay


class Streak:
    """A vertical speed line left by a teleport."""
    __slots__ = ("x", "top", "bottom", "life", "max_life", "delay")

    def __init__(self, x, top, bottom, life, delay=0.0):
        self.x, self.top, self.bottom = x, top, bottom
        self.life = self.max_life = life
        self.delay = delay


class Effects:
    def __init__(self, font_factory):
        self.font = font_factory
        self.particles = []
        self.texts = []
        self.ghosts = []
        self.streaks = []

    def burst(self, x, y, color, n=14, speed=320, size=4, life=0.5):
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            s = random.uniform(0.3, 1.0) * speed
            self.particles.append(Particle(x, y, math.cos(a) * s, math.sin(a) * s - 120,
                                           random.uniform(0.6, 1.0) * life, color, size))

    def sparks(self, x, y, color, n=8):
        self.burst(x, y, color, n=n, speed=420, size=3, life=0.25)

    def teleport(self, image, start, end, arrive_delay=0.08):
        """Instant transmission: vanish from `start` (a rect), reappear at `end`."""
        glow = image.copy()
        glow.fill((110, 190, 255), special_flags=pygame.BLEND_RGB_ADD)
        self.ghosts.append(Ghost(glow, start, "out", 0.16))
        self.ghosts.append(Ghost(glow, end, "in", 0.14, delay=max(0.0, arrive_delay - 0.03)))
        for rect, delay in ((start, 0.0), (end, arrive_delay)):
            for _ in range(5):
                x = rect.centerx + random.uniform(-0.35, 0.35) * rect.width
                h = random.uniform(0.6, 1.3) * rect.height
                top = rect.centery - h / 2 + random.uniform(-20, 20)
                self.streaks.append(Streak(x, top, top + h, random.uniform(0.12, 0.22), delay + random.uniform(0, 0.04)))
        self.sparks(start.centerx, start.centery, (170, 225, 255), 6)

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
        for g in self.ghosts + self.streaks:
            if g.delay > 0:
                g.delay -= dt
            else:
                g.life -= dt
        self.ghosts = [g for g in self.ghosts if g.life > 0]
        self.streaks = [g for g in self.streaks if g.life > 0]

    def draw(self, surf):
        for st in self.streaks:
            if st.delay > 0:
                continue
            k = st.life / st.max_life
            col = (int(150 + 105 * k), int(210 + 45 * k), 255)
            pygame.draw.line(surf, col, (round(st.x), round(st.top)), (round(st.x), round(st.bottom)), 2 if k > 0.5 else 1)
        for g in self.ghosts:
            if g.delay > 0:
                continue
            t = 1 - g.life / g.max_life                     # 0 -> 1
            grow = t if g.mode == "in" else 1 - t           # 1 = full width
            if int(t * 30) % 3 == 2:
                continue                                     # flicker
            w, h = g.image.get_size()
            img = pygame.transform.scale(g.image, (max(2, round(w * grow)), round(h * (1.35 - 0.35 * grow))))
            img.set_alpha(int(110 + 145 * grow) if g.mode == "out" else int(240 * (1 - t)))   # 'in' fades into Ren
            surf.blit(img, img.get_rect(midbottom=g.rect.midbottom))
        self._draw_particles(surf)

    def _draw_particles(self, surf):
        for p in self.particles:
            r = max(1, round(p.size * p.life / p.max_life))
            pygame.draw.circle(surf, p.color, (round(p.x), round(p.y)), r)
        for t in self.texts:
            alpha = 255 * min(1.0, t.life / (t.max_life * 0.4))
            t.surf.set_alpha(int(alpha))
            surf.blit(t.surf, t.surf.get_rect(center=(round(t.x), round(t.y))))
