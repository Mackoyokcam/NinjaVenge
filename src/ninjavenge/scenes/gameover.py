import pygame

from .. import config as C
from .. import highscore
from ..app import Scene
from ..ui import Background, MenuList, dim, draw_text, pulse


class GameOverScene(Scene):
    def __init__(self, app, score_keeper, wave, ryo_earned=0):
        super().__init__(app)
        self.score = score_keeper.score
        self.best_streak = score_keeper.best_streak
        self.wave = wave
        self.ryo_earned = ryo_earned
        self.table, self.rank = highscore.submit(self.score, wave) if self.score > 0 else (highscore.load(), None)
        self.bg = Background()
        self.t = 0.0
        self.menu = MenuList(app, [
            ("Retry", self.retry),
            ("Dojo Shop", self.shop),
            ("Main Menu", self.main_menu),
            ("Quit", app.quit),
        ], C.SCREEN_W // 2 - 300, 470)
        pygame.mouse.set_visible(True)

    def retry(self):
        from .game import GameScene
        self.app.change(GameScene(self.app))

    def shop(self):
        from .shop import ShopScene
        self.app.push(ShopScene(self.app))

    def main_menu(self):
        from .menu import MenuScene
        self.app.change(MenuScene(self.app))

    def handle_event(self, event):
        self.menu.handle_event(event)

    def update(self, dt):
        self.t += dt
        self.bg.update(dt)

    def draw(self, surf):
        self.bg.draw(surf)
        dim(surf, 170)
        cx = C.SCREEN_W // 2
        draw_text(surf, self.app.font(110), "GAME OVER", C.RED, center=(cx, 120))
        f = self.app.font(40)
        left = cx - 300
        draw_text(surf, f, f"Score: {self.score:,}", C.WHITE, center=(left, 250))
        draw_text(surf, f, f"Reached wave {self.wave}", C.WHITE, center=(left, 305))
        draw_text(surf, f, f"Best combo: {self.best_streak} kills", C.WHITE, center=(left, 360))
        if self.rank == 0:
            col = tuple(int(c * (0.6 + 0.4 * pulse(self.t, 6))) for c in C.GOLD)
            draw_text(surf, self.app.font(46), "NEW HIGH SCORE!", col, center=(left, 420))
        self.menu.draw(surf)

        # high-score table
        right = cx + 300
        draw_text(surf, self.app.font(46), "High Scores", C.GOLD, center=(right, 250))
        for i, e in enumerate(self.table):
            col = C.GOLD if i == self.rank else C.WHITE
            draw_text(surf, f, f"{i + 1}.  {e['score']:>8,}   wave {e.get('wave', '?')}", col,
                      center=(right, 310 + i * 48))

        # currency
        draw_text(surf, self.app.font(46), f"+{self.ryo_earned} ryo earned", C.GOLD, center=(right, 600))
        draw_text(surf, f, f"Balance: {self.app.profile.ryo} ryo - spend it in the Dojo Shop", C.WHITE,
                  center=(right, 648))
