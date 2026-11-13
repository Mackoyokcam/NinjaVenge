import pygame

from .. import config as C
from .. import highscore
from ..app import Scene
from ..ui import dim, draw_text

STORY = [
    "You are Ren, the last ninja of the Otaku clan.",
    "Cowboys, robots and jack-o-lanterns raided your home. Now they use its roads.",
    "Stop every one of them. Each that slips past costs you a heart.",
]

ENEMIES = [
    ("Cowboy", "Fast and fragile. Flashes '!' then shoots - dodge, or slash the bullet to send it back."),
    ("Robot", "Armored. A kunai staggers it (blue); slashes do double damage while it's staggered."),
    ("Jack", "Comes back to life! Slash the fallen pumpkin before the ring closes - kunai pass through it."),
    ("Bosses", "Every 5 waves. A kunai during their '!' wind-up interrupts them. Cost 3 hearts if they pass."),
]

CONTROLS = [
    ("Left / Right", "Run"),
    ("Up / Down", "Hop to the next lane (attack or throw mid-air for a jump attack)"),
    ("A  (or J / Z)", "Katana - hits everything in reach, sends bullets back where they came from"),
    ("S  (or K / X)", "Throw kunai (short cooldown)"),
    ("Esc / P", "Pause"),
]

TIPS = "Chain kills to raise your multiplier (up to x5). Kills and cleared waves earn ryo for the Dojo Shop."


class _Overlay(Scene):
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
            self.app.pop()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.app.pop()

    def draw_under(self, surf):
        self.app.stack[-2].draw(surf)
        dim(surf, 238)


class AboutScene(_Overlay):
    def draw(self, surf):
        self.draw_under(surf)
        f, fb, fs = self.app.font(30), self.app.font(34), self.app.font(26)
        draw_text(surf, self.app.font(64), "How to Play", C.UI_ACCENT, center=(C.SCREEN_W // 2, 60))
        y = 115
        for line in STORY:
            draw_text(surf, f, line, C.WHITE, center=(C.SCREEN_W // 2, y))
            y += 34
        y += 20
        draw_text(surf, fb, "Controls", C.GOLD, topleft=(160, y))
        y += 44
        for key, what in CONTROLS:
            draw_text(surf, f, key, C.CYAN, topleft=(160, y))
            draw_text(surf, f, what, C.WHITE, topleft=(400, y))
            y += 34
        y += 20
        draw_text(surf, fb, "Enemies", C.GOLD, topleft=(160, y))
        y += 44
        for name, what in ENEMIES:
            draw_text(surf, f, name, C.ORANGE, topleft=(160, y))
            draw_text(surf, f, what, C.WHITE, topleft=(400, y))
            y += 34
        y += 20
        draw_text(surf, f, TIPS, C.GOLD, center=(C.SCREEN_W // 2, y))
        draw_text(surf, fs, "Press Esc to go back", C.GREY, center=(C.SCREEN_W // 2, C.SCREEN_H - 30))


class HighScoreScene(_Overlay):
    def __init__(self, app):
        super().__init__(app)
        self.table = highscore.load()

    def draw(self, surf):
        self.draw_under(surf)
        draw_text(surf, self.app.font(72), "High Scores", C.GOLD, center=(C.SCREEN_W // 2, 160))
        f = self.app.font(44)
        if not self.table:
            draw_text(surf, f, "No scores yet - go make some!", C.WHITE, center=(C.SCREEN_W // 2, 320))
        for i, e in enumerate(self.table):
            draw_text(surf, f, f"{i + 1}.  {e['score']:>8,}    wave {e.get('wave', '?')}", C.WHITE,
                      center=(C.SCREEN_W // 2, 270 + i * 60))
        draw_text(surf, self.app.font(26), "Press Esc to go back", C.GREY, center=(C.SCREEN_W // 2, C.SCREEN_H - 40))
