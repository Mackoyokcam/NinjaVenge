"""The Dojo Shop: spend ryo on permanent upgrades between runs."""
import pygame

from .. import config as C
from ..app import Scene
from ..ui import Background, dim, draw_text
from ..upgrades import UPGRADES

ROW_W, ROW_H, ROW_GAP = 1000, 92, 14
TOP = 175


class ShopScene(Scene):
    """Pushed on top of the menu or game-over screen; Esc returns there."""

    def __init__(self, app):
        super().__init__(app)
        self.bg = Background()
        self.profile = app.profile
        self.selected = 0
        self.message, self.message_t, self.message_color = "", 0.0, C.WHITE
        self.rows = []
        for i in range(len(UPGRADES) + 1):  # +1 for "Back"
            r = pygame.Rect(0, 0, ROW_W, ROW_H if i < len(UPGRADES) else 54)
            r.midtop = (C.SCREEN_W // 2, TOP + i * (ROW_H + ROW_GAP))
            self.rows.append(r)
        pygame.mouse.set_visible(True)

    # ------------------------------------------------------------------ actions
    def activate(self, index):
        if index == len(UPGRADES):
            self.app.pop()
            return
        u = UPGRADES[index]
        p = self.profile
        level = p.level(u.key)
        if u.toggle and level >= u.max_level:
            p.toggle(u.key)
            self.flash(f"{u.name} {'ON' if p.is_enabled(u.key) else 'OFF'}", C.CYAN)
            self.app.assets.play("dink.wav")
        elif level >= u.max_level:
            self.flash(f"{u.name} is maxed out", C.GREY)
        elif p.buy(u.key):
            self.flash(f"Bought {u.name}!", C.GOLD)
            self.app.assets.play("attack.wav")
        else:
            self.flash(f"Not enough ryo - need {u.cost(level) - p.ryo} more", C.RED)
            self.app.assets.play("dink.wav")

    def flash(self, text, color):
        self.message, self.message_t, self.message_color = text, 2.0, color

    def handle_event(self, event):
        n = len(self.rows)
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.pop()
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % n
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % n
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.activate(self.selected)
        elif event.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self.rows):
                if r.collidepoint(event.pos):
                    self.selected = i
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.rows):
                if r.collidepoint(event.pos):
                    self.selected = i
                    self.activate(i)

    def update(self, dt):
        self.bg.update(dt)
        self.message_t = max(0.0, self.message_t - dt)

    # ------------------------------------------------------------------ draw
    def draw(self, surf):
        self.bg.draw(surf)
        dim(surf, 200)
        f_title, f_name, f_desc, f_small = self.app.font(72), self.app.font(36), self.app.font(26), self.app.font(24)
        draw_text(surf, f_title, "Dojo Shop", C.UI_ACCENT, center=(C.SCREEN_W // 2, 70))
        draw_text(surf, f_name, f"Ryo: {self.profile.ryo}", C.GOLD, center=(C.SCREEN_W // 2, 128))

        for i, (u, r) in enumerate(zip(UPGRADES, self.rows)):
            self._draw_row(surf, u, r, i == self.selected, f_name, f_desc, f_small)

        back = self.rows[-1]
        active = self.selected == len(UPGRADES)
        back = back.inflate(-ROW_W + 260, 0)
        pygame.draw.rect(surf, C.UI_ACCENT if active else (30, 30, 44), back, border_radius=10)
        pygame.draw.rect(surf, C.WHITE if active else (80, 80, 100), back, 2, border_radius=10)
        draw_text(surf, f_name, "Back", C.WHITE, center=back.center)
        self.rows[-1] = back

        if self.message_t > 0:
            draw_text(surf, f_name, self.message, self.message_color, center=(C.SCREEN_W // 2, C.SCREEN_H - 30))
        else:
            draw_text(surf, f_small, "Up/Down + Enter, or click. Esc to go back. Ryo is earned from kills and cleared waves.",
                      C.GREY, center=(C.SCREEN_W // 2, C.SCREEN_H - 30))

    def _draw_row(self, surf, u, r, active, f_name, f_desc, f_small):
        p = self.profile
        level = p.level(u.key)
        maxed = level >= u.max_level
        pygame.draw.rect(surf, (0, 0, 0), r.move(4, 4), border_radius=12)
        pygame.draw.rect(surf, (52, 26, 40) if active else (26, 26, 38), r, border_radius=12)
        pygame.draw.rect(surf, C.UI_ACCENT if active else (70, 70, 90), r, 2, border_radius=12)
        draw_text(surf, f_name, u.name, C.WHITE, topleft=(r.left + 24, r.top + 16))
        draw_text(surf, f_desc, u.description, (200, 200, 210), topleft=(r.left + 24, r.top + 54))

        # level pips
        for n in range(u.max_level):
            pip = pygame.Rect(0, 0, 22, 22)
            pip.topleft = (r.left + 330 + n * 30, r.top + 18)
            pygame.draw.rect(surf, C.GOLD if n < level else (60, 60, 75), pip, border_radius=4)
            pygame.draw.rect(surf, C.BLACK, pip, 1, border_radius=4)

        # price / status
        right = (r.right - 24, r.centery)
        if u.toggle and maxed:
            on = p.is_enabled(u.key)
            draw_text(surf, f_name, "ON" if on else "OFF", C.CYAN if on else C.GREY, midright=right)
            draw_text(surf, f_small, "Enter to toggle", C.GREY, midright=(right[0], right[1] + 28))
        elif maxed:
            draw_text(surf, f_name, "MAX", C.GOLD, midright=right)
        else:
            cost = u.cost(level)
            draw_text(surf, f_name, f"{cost} ryo", C.GOLD if p.ryo >= cost else C.RED, midright=right)
