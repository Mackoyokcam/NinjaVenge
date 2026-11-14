import pygame

from .. import config as C
from .. import highscore
from ..app import Scene
from ..ui import dim, draw_text

STORY = [
    "You are Ren, the last ninja of the Otaku clan.",
    "Cowboys, robots and jack-o-lanterns raided your home. Now they use its roads.",
    "Their warlords - Sir Clank, Rex, and the rival kunoichi Kage - lead the raids.",
    "Stop every one of them. Each that slips past costs you a heart.",
]

ENEMIES = [
    ("Cowboy", "Fast and fragile. Flashes '!' then shoots - dodge, or slash the bullet to send it back."),
    ("Robot", "Armored. A kunai staggers it (blue); slashes do double damage while it's staggered."),
    ("Jack", "Comes back to life! Slash the fallen pumpkin before the ring closes - kunai pass through it."),
    ("Bosses", "Every 5 waves. A kunai during their '!' wind-up interrupts them. Cost 3 hearts if they pass."),
    ("Kage", "Hunts you across lanes. Slash her shuriken back, and strike right after she attacks."),
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


class CreditsScene(_Overlay):
    """Scrolls the credits up the screen. Arrows / mouse wheel scroll by hand, Esc goes back."""

    SPEED = 45          # pixels per second of auto-scroll
    TOP, BOTTOM = 110, C.SCREEN_H - 60

    def __init__(self, app):
        super().__init__(app)
        self.page = self._render()
        self.scroll = 0.0
        self.auto = True

    @property
    def max_scroll(self):
        return max(0, self.page.get_height() - (self.BOTTOM - self.TOP))

    def _render(self):
        from ..credits import GAME, LICENSES, SECTIONS
        f = self.app.font
        rows = [(f(34), C.GOLD, GAME[0], 38), (f(32), C.WHITE, GAME[1], 60)]
        for section, entries in SECTIONS:
            rows.append((f(44), C.UI_ACCENT, section, 50))
            for work, who, source in entries:
                rows.append((f(32), C.CYAN, work, 32))
                rows.append((f(27), C.WHITE, who, 26 if source else 40))
                if source:
                    rows.append((f(23), C.GREY, source, 40))
            rows[-1] = rows[-1][:3] + (rows[-1][3] + 24,)
        rows.append((f(34), C.GOLD, "Licenses", 38))
        rows += [(f(25), C.WHITE, line, 28) for line in LICENSES]
        rows[-1] = rows[-1][:3] + (rows[-1][3] + 30,)
        rows.append((f(30), C.GOLD, "Thanks for playing!", 40))
        page = pygame.Surface((C.SCREEN_W, sum(r[3] for r in rows) + 20), pygame.SRCALPHA)
        y = 0
        for font, color, text, step in rows:
            draw_text(page, font, text, color, center=(C.SCREEN_W // 2, y + font.get_height() // 2))
            y += step
        return page

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_s):
            self.auto = False
            step = 80 if event.key in (pygame.K_DOWN, pygame.K_s) else -80
            self.scroll = min(self.max_scroll, max(0.0, self.scroll + step))
        elif event.type == pygame.MOUSEWHEEL:
            self.auto = False
            self.scroll = min(self.max_scroll, max(0.0, self.scroll - event.y * 60))
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
            pass                        # wheel clicks from older SDL; MOUSEWHEEL handles scrolling
        else:
            super().handle_event(event)

    def update(self, dt):
        if self.auto:
            self.scroll = min(self.max_scroll, self.scroll + self.SPEED * dt)

    def draw(self, surf):
        self.draw_under(surf)
        draw_text(surf, self.app.font(64), "Credits", C.UI_ACCENT, center=(C.SCREEN_W // 2, 60))
        view = pygame.Rect(0, self.scroll, C.SCREEN_W, self.BOTTOM - self.TOP)
        surf.blit(self.page, (0, self.TOP), view)
        band = pygame.Surface((C.SCREEN_W, 1), pygame.SRCALPHA)
        for i in range(28):                                    # fade lines in and out at the edges
            band.fill((0, 0, 0, int(235 * (1 - i / 28))))
            surf.blit(band, (0, self.TOP + i))
            surf.blit(band, (0, self.BOTTOM - 1 - i))
        draw_text(surf, self.app.font(26), "Up / Down to scroll    Esc to go back", C.GREY,
                  center=(C.SCREEN_W // 2, C.SCREEN_H - 30))
