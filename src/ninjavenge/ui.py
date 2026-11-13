"""Reusable UI: text, keyboard+mouse menus, the backdrop, and the in-game HUD."""
import math
import random

import pygame

from . import config as C


def draw_text(surf, font, text, color, shadow=True, **pos):
    """Blit text positioned by any Rect attribute, e.g. center=(x, y) or topleft=(x, y)."""
    img = font.render(text, True, color)
    rect = img.get_rect(**pos)
    if shadow:
        surf.blit(font.render(text, True, (0, 0, 0)), rect.move(2, 2))
    surf.blit(img, rect)
    return rect


class MenuList:
    """Vertical button list. Arrow keys / W,S + Enter, or mouse hover + click."""

    def __init__(self, app, options, center_x, top, width=280, height=54, gap=16):
        self.app = app
        self.options = options          # list of (label, callback)
        self.selected = 0
        self.rects = []
        for i in range(len(options)):
            r = pygame.Rect(0, 0, width, height)
            r.midtop = (center_x, top + i * (height + gap))
            self.rects.append(r)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.options)
                return True
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.options)
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.options[self.selected][1]()
                return True
        elif event.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self.rects):
                if r.collidepoint(event.pos):
                    self.selected = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.rects):
                if r.collidepoint(event.pos):
                    self.selected = i
                    self.options[i][1]()
                    return True
        return False

    def draw(self, surf):
        font = self.app.font(36)
        for i, ((label, _), r) in enumerate(zip(self.options, self.rects)):
            active = i == self.selected
            bg = C.UI_ACCENT if active else (30, 30, 44)
            pygame.draw.rect(surf, (0, 0, 0), r.move(4, 4), border_radius=10)
            pygame.draw.rect(surf, bg, r, border_radius=10)
            pygame.draw.rect(surf, C.WHITE if active else (80, 80, 100), r, 2, border_radius=10)
            draw_text(surf, font, label, C.WHITE, center=r.center)


class Background:
    """Night sky, moon, mountains and wooden walkways; clouds drift."""

    def __init__(self, seed=7):
        rng = random.Random(seed)
        self.static = pygame.Surface((C.SCREEN_W, C.SCREEN_H)).convert()
        s = self.static
        # sky gradient
        top, bottom = (10, 8, 30), (70, 30, 60)
        for y in range(C.SCREEN_H):
            t = y / C.SCREEN_H
            col = [int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)]
            pygame.draw.line(s, col, (0, y), (C.SCREEN_W, y))
        for _ in range(140):
            x, y = rng.randrange(C.SCREEN_W), rng.randrange(0, 420)
            b = rng.randrange(120, 255)
            s.set_at((x, y), (b, b, b))
        # moon
        pygame.draw.circle(s, (255, 235, 200), (1220, 130), 70)
        pygame.draw.circle(s, (240, 210, 170), (1195, 110), 14)
        pygame.draw.circle(s, (240, 210, 170), (1245, 160), 9)
        # two mountain ranges
        for color, base, amp, step in (((40, 22, 50), 420, 160, 120), ((26, 14, 34), 520, 120, 80)):
            pts = [(0, C.SCREEN_H)]
            x = 0
            while x <= C.SCREEN_W + step:
                pts.append((x, base - rng.randrange(amp // 3, amp)))
                x += step
            pts.append((C.SCREEN_W, C.SCREEN_H))
            pygame.draw.polygon(s, color, pts)
        # ground
        ground = C.LANE_FLOORS[0]
        pygame.draw.rect(s, (24, 16, 18), (0, ground, C.SCREEN_W, C.SCREEN_H - ground))
        # walkways
        for floor in C.LANE_FLOORS:
            self._walkway(s, floor, ground_lane=(floor == ground))
        self.clouds = [[rng.uniform(0, C.SCREEN_W), rng.uniform(60, 320), rng.uniform(8, 22), rng.uniform(0.6, 1.4)]
                       for _ in range(6)]

    @staticmethod
    def _walkway(s, floor, ground_lane):
        plank = (92, 52, 34)
        edge = (140, 84, 50)
        t = C.LANE_THICKNESS
        if not ground_lane:
            for x in range(40, C.SCREEN_W, 220):
                pygame.draw.rect(s, (50, 28, 22), (x, floor, 10, 42))  # posts
        pygame.draw.rect(s, plank, (0, floor, C.SCREEN_W, t))
        pygame.draw.line(s, edge, (0, floor), (C.SCREEN_W, floor), 2)
        for x in range(0, C.SCREEN_W, 48):
            pygame.draw.line(s, (60, 34, 24), (x, floor + 2), (x, floor + t), 1)
        # lanterns at both ends mark where enemies come from
        for x in (18, C.SCREEN_W - 18):
            pygame.draw.line(s, (60, 40, 30), (x, floor), (x, floor - 60), 3)
            pygame.draw.circle(s, (255, 120, 40), (x, floor - 66), 9)
            pygame.draw.circle(s, (255, 200, 120), (x, floor - 66), 4)

    def update(self, dt):
        for c in self.clouds:
            c[0] += c[2] * dt
            if c[0] > C.SCREEN_W + 200:
                c[0] = -200

    def draw(self, surf):
        surf.blit(self.static, (0, 0))
        for x, y, _, size in self.clouds:
            for dx, dy, r in ((0, 0, 34), (30, 8, 26), (-30, 8, 24), (60, 14, 18)):
                pygame.draw.circle(surf, (60, 40, 80), (int(x + dx * size), int(y + dy * size)), int(r * size))


class Hud:
    def __init__(self, app):
        self.app = app
        heart = app.assets.image("heart.png")
        self.heart = heart
        self.heart_empty = heart.copy()
        self.heart_empty.fill((70, 70, 80, 120), special_flags=pygame.BLEND_RGBA_MULT)
        kunai = app.assets.image("Kunai.png")
        self.kunai = kunai
        self.kunai_dim = kunai.copy()
        self.kunai_dim.fill((90, 90, 90, 160), special_flags=pygame.BLEND_RGBA_MULT)

    def draw(self, surf, world, wave_number=None, banner=None, banner_t=0.0):
        f_small, f_med, f_big = self.app.font(26), self.app.font(36), self.app.font(64)

        # hearts
        for i in range(world.loadout.max_hearts):
            img = self.heart if i < world.hearts else self.heart_empty
            surf.blit(img, (14 + i * 56, 12))
        if not world.tutorial:
            draw_text(surf, f_small, f"Ryo this run: {world.ryo_earned}", C.GOLD, topleft=(16, 62))

        # score + combo
        draw_text(surf, f_med, f"{world.score.score:,}", C.WHITE, center=(C.SCREEN_W // 2, 28))
        mult = world.score.multiplier
        bar = pygame.Rect(0, 0, 160, 6)
        bar.midtop = (C.SCREEN_W // 2, 50)
        pygame.draw.rect(surf, (50, 50, 60), bar)
        fill = bar.copy()
        fill.width = int(bar.width * world.score.streak_progress)
        pygame.draw.rect(surf, C.ORANGE, fill)
        if mult > 1:
            draw_text(surf, f_med, f"x{mult}", C.ORANGE, midleft=(bar.right + 12, bar.centery))

        # wave + pause hint
        if wave_number is not None:
            draw_text(surf, f_med, f"WAVE {wave_number}", C.WHITE, topright=(C.SCREEN_W - 20, 12))
        draw_text(surf, f_small, "Esc: Pause", C.GREY, topright=(C.SCREEN_W - 20, 46))

        # kunai cooldown (bottom-left, in the ground strip)
        p = world.player
        x, y = 24, C.SCREEN_H - 50
        surf.blit(self.kunai if p.kunai_ready else self.kunai_dim, (x, y))
        if not p.kunai_ready:
            frac = 1 - p.kunai_cd / p.loadout.kunai_cooldown
            pygame.draw.rect(surf, (50, 50, 60), (x, y + 22, 80, 5))
            pygame.draw.rect(surf, C.CYAN, (x, y + 22, int(80 * frac), 5))
        # katana cooldown, just above the kunai
        ky = y - 26
        blade = C.WHITE if p.attack_ready else (110, 110, 120)
        pygame.draw.line(surf, blade, (x + 20, ky), (x + 80, ky - 8), 3)
        pygame.draw.line(surf, (150, 40, 50), (x, ky + 3), (x + 18, ky), 5)
        pygame.draw.line(surf, C.GOLD, (x + 18, ky - 5), (x + 20, ky + 5), 3)
        if not p.attack_ready and p.loadout.attack_cooldown > 0:
            frac = 1 - p.attack_cd / p.loadout.attack_cooldown
            pygame.draw.rect(surf, (50, 50, 60), (x, ky + 8, 80, 4))
            pygame.draw.rect(surf, C.WHITE, (x, ky + 8, int(80 * frac), 4))
        draw_text(surf, f_small, "Arrows: move / switch lane    A: katana    S: kunai", C.GREY,
                  midleft=(130, y + 8))

        # boss bar
        boss = world.boss
        if boss:
            r = pygame.Rect(0, 0, 600, 18)
            r.midtop = (C.SCREEN_W // 2, 72)
            pygame.draw.rect(surf, (40, 20, 20), r)
            inner = r.copy()
            inner.width = int(r.width * max(0, boss.hp) / boss.max_hp)
            pygame.draw.rect(surf, C.RED, inner)
            pygame.draw.rect(surf, C.WHITE, r, 2)
            draw_text(surf, f_small, boss.title, C.WHITE, midtop=(r.centerx, r.bottom + 4))

        # wave banner
        if banner:
            alpha = min(1.0, banner_t * 3, (2.5 - banner_t) * 2)
            if alpha > 0:
                title = f_big.render(banner[0], True, C.WHITE)
                layer = pygame.Surface((C.SCREEN_W, 140), pygame.SRCALPHA)
                layer.fill((0, 0, 0, 140))
                layer.blit(title, title.get_rect(center=(C.SCREEN_W // 2, 50)))
                if banner[1]:
                    sub = f_med.render(banner[1], True, C.GOLD)
                    layer.blit(sub, sub.get_rect(center=(C.SCREEN_W // 2, 105)))
                layer.set_alpha(int(255 * alpha))
                surf.blit(layer, (0, 140))


def dim(surf, alpha=160):
    shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    shade.fill((0, 0, 0, alpha))
    surf.blit(shade, (0, 0))


def pulse(t, speed=3.0):
    return 0.5 + 0.5 * math.sin(t * speed)
