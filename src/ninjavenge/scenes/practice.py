"""Boss Practice: jump straight into any boss fight (no ryo, no high score)."""
import pygame

from .. import config as C
from ..app import Scene
from ..ui import Background, MenuList, draw_text
from ..waves import boss_wave

BOSSES = [("Sir Clank", "knight"), ("Rex", "dino"), ("Kage", "kage")]


class PracticeScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.bg = Background()
        options = [(f"{label}  (wave {boss_wave(name)})", lambda n=name: self.fight(n)) for label, name in BOSSES]
        self.menu = MenuList(app, options + [("Back", self.back)], C.SCREEN_W // 2, 300, width=380)
        pygame.mouse.set_visible(True)
        app.assets.music.stop()

    def fight(self, name):
        from .game import GameScene
        self.app.change(GameScene(self.app, practice_boss=name))

    def back(self):
        from .menu import MenuScene
        self.app.change(MenuScene(self.app))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.back()
            return
        self.menu.handle_event(event)

    def update(self, dt):
        self.bg.update(dt)

    def draw(self, surf):
        self.bg.draw(surf)
        draw_text(surf, self.app.font(90), "Boss Practice", C.UI_ACCENT, center=(C.SCREEN_W // 2, 150))
        draw_text(surf, self.app.font(30), "Fight any boss with your current upgrades. No ryo or high scores.",
                  C.WHITE, center=(C.SCREEN_W // 2, 225))
        self.menu.draw(surf)
