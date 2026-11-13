import pygame

from .. import config as C
from .. import highscore
from ..animation import Animation
from ..app import Scene
from ..ui import Background, MenuList, draw_text


class MenuScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.bg = Background()
        self.menu = MenuList(app, [
            ("Start", self.start),
            ("Dojo Shop", self.shop),
            ("Tutorial", self.tutorial),
            ("How to Play", self.about),
            ("High Scores", self.scores),
            ("Quit", app.quit),
        ], C.SCREEN_W // 2, 330)
        self.ninja = Animation(app.assets.animation("ninja/right/idle"), 1.0)
        self.best = highscore.best()
        pygame.mouse.set_visible(True)
        app.assets.stop_music()

    def start(self):
        from .game import GameScene
        self.app.change(GameScene(self.app))

    def tutorial(self):
        from .tutorial import TutorialScene
        self.app.change(TutorialScene(self.app))

    def shop(self):
        from .shop import ShopScene
        self.app.push(ShopScene(self.app))

    def about(self):
        from .info import AboutScene
        self.app.push(AboutScene(self.app))

    def scores(self):
        from .info import HighScoreScene
        self.app.push(HighScoreScene(self.app))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.quit()
            return
        self.menu.handle_event(event)

    def update(self, dt):
        self.bg.update(dt)
        self.ninja.update(dt)

    def draw(self, surf):
        self.bg.draw(surf)
        draw_text(surf, self.app.font(120), "NINJAVENGE", C.UI_ACCENT, center=(C.SCREEN_W // 2, 150))
        draw_text(surf, self.app.font(32), "Defend the roads home. Leave none standing.", C.WHITE,
                  center=(C.SCREEN_W // 2, 230))
        img = self.ninja.frame(1)
        surf.blit(img, img.get_rect(midbottom=(C.SCREEN_W // 2 - 330, C.LANE_FLOORS[0])))
        info = f"Ryo: {self.app.profile.ryo}" + (f"     Best: {self.best:,}" if self.best else "")
        draw_text(surf, self.app.font(30), info, C.GOLD, center=(C.SCREEN_W // 2, 290))
        self.menu.draw(surf)
