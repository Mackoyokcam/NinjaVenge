import pygame

from .. import config as C
from ..app import Scene
from ..ui import MenuList, dim, draw_text


class PauseScene(Scene):
    """Overlay pushed on top of the game; the game underneath is frozen, not reset."""

    def __init__(self, app, game):
        super().__init__(app)
        self.game = game
        self.menu = MenuList(app, [
            ("Resume", self.resume),
            ("Restart", self.restart),
            ("Main Menu", self.main_menu),
            ("Quit", app.quit),
        ], C.SCREEN_W // 2, 320)
        app.assets.music.pause()
        pygame.mouse.set_visible(True)

    def resume(self):
        self.app.pop()
        self.app.assets.music.resume()
        pygame.mouse.set_visible(False)

    def restart(self):
        self.game.bank_earnings()
        self.app.change(type(self.game)(self.app))

    def main_menu(self):
        self.game.bank_earnings()
        from .menu import MenuScene
        self.app.change(MenuScene(self.app))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p, pygame.K_F1):
            self.resume()
            return
        self.menu.handle_event(event)

    def draw(self, surf):
        self.game.draw(surf)
        dim(surf)
        draw_text(surf, self.app.font(90), "PAUSED", C.WHITE, center=(C.SCREEN_W // 2, 230))
        self.menu.draw(surf)
