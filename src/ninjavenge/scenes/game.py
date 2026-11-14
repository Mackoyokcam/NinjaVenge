import pygame

from .. import config as C
from ..app import Scene
from ..entities.sprite_utils import anchored_rect
from ..stages import MEDIEVAL, music_for, territory
from ..ui import FadingBackground, Hud
from ..waves import WaveDirector, boss_wave
from ..world import World

LEFT_KEYS = (pygame.K_LEFT,)
RIGHT_KEYS = (pygame.K_RIGHT,)
UP_KEYS = (pygame.K_UP,)
DOWN_KEYS = (pygame.K_DOWN,)
ATTACK_KEYS = (pygame.K_a, pygame.K_j, pygame.K_z)
THROW_KEYS = (pygame.K_s, pygame.K_k, pygame.K_x)
PAUSE_KEYS = (pygame.K_ESCAPE, pygame.K_p, pygame.K_F1)

GAME_OVER_DELAY = 2.5
PRACTICE_WIN_DELAY = 3.0
INPUT_BUFFER = 0.18  # seconds an early button press is remembered


class GameScene(Scene):
    tutorial = False

    def __init__(self, app, rng=None, practice_boss=None):
        super().__init__(app)
        self.practice_boss = practice_boss      # "knight" / "dino" / "kage": Boss Practice run
        self.practice_won = None                # seconds since the practice boss fell
        self.world = World(app, tutorial=self.tutorial, loadout=app.profile.loadout())
        start = boss_wave(practice_boss) if practice_boss else 1
        self.director = None if self.tutorial else WaveDirector(rng=rng, start_wave=start)
        self.bg = FadingBackground(app.assets, self.stage()[0])
        self.hud = Hud(app)
        self.canvas = pygame.Surface((C.SCREEN_W, C.SCREEN_H)).convert()
        self.buffered = None
        self.banked = False
        pygame.mouse.set_visible(False)
        app.assets.music.stop()
        app.assets.music.play(self.stage()[1])

    def stage(self):
        """(territory, music key) for the current wave."""
        if not self.director:
            return MEDIEVAL, "tutorial"
        n = self.director.number
        return territory(n), music_for(n)

    # ------------------------------------------------------------------ input
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in PAUSE_KEYS:
            if self.world.player.alive:
                from .pause import PauseScene
                self.app.push(PauseScene(self.app, self))
            return
        action = None
        if event.key in UP_KEYS:
            action = "up"
        elif event.key in DOWN_KEYS:
            action = "down"
        elif event.key in ATTACK_KEYS:
            action = "attack"
        elif event.key in THROW_KEYS:
            action = "throw"
        if action and not self.do_action(action):
            # pressed slightly too early: remember it briefly so it fires when Ren is free
            self.buffered = (action, INPUT_BUFFER)

    def do_action(self, action):
        p, w = self.world.player, self.world
        if not p.alive:
            return False
        if action in ("up", "down"):
            img = p.current_frame()
            start = anchored_rect(img, p.x, p.y, p.facing, C.PLAYER_ANCHOR)
            step = 1 if action == "up" else -1
            from_lane = p.lane
            if not p.try_switch_lane(step):
                return False
            w.emit("switch")
            if p.loadout.shinobi:
                # instant transmission: flicker out here, flicker in on the next lane
                w.sfx.play("teleport")
                end = start.move(0, C.LANE_FLOORS[from_lane + step] - C.LANE_FLOORS[from_lane])
                w.effects.teleport(img, start, end, arrive_delay=p.switch_time)
            else:
                w.sfx.play("jump")
        elif action == "attack":
            if not p.try_attack():
                return False
            w.sfx.play("attack")
            w.emit("attack")
        elif action == "throw":
            if not p.try_throw():
                return False
            w.emit("throw")
        if action in ("attack", "throw") and p.airborne:
            w.emit("air_attack")
        return True

    def read_movement(self):
        keys = pygame.key.get_pressed()
        left = any(keys[k] for k in LEFT_KEYS)
        right = any(keys[k] for k in RIGHT_KEYS)
        return (1 if right else 0) - (1 if left else 0)

    # ------------------------------------------------------------------ update
    def update(self, dt):
        theme, track = self.stage()
        self.bg.set_theme(theme)
        if self.world.player.alive:
            self.app.assets.music.play(track)
        self.bg.update(dt)
        w = self.world
        w.player.set_move(self.read_movement() if w.player.alive else 0)
        if self.buffered:
            action, t = self.buffered
            self.buffered = None if self.do_action(action) or t - dt <= 0 else (action, t - dt)
        if self.director and not w.game_over:
            before = self.director.number
            for spawn in self.director.update(dt, w.alive_enemies):
                w.spawn(spawn, self.director.wave)
            if self.director.number != before and self.practice_boss:
                self.director.number = before         # stay put: practice is one fight
                self.director.state, self.director._pending = self.director.CLEARING, []
                if self.practice_won is None:
                    self.practice_won = 0.0
                    w.effects.text(C.SCREEN_W // 2, 320, "BOSS DEFEATED!", C.GOLD, size=56, life=PRACTICE_WIN_DELAY)
            elif self.director.number != before:
                w.waves_cleared = before
                w.effects.text(C.SCREEN_W // 2, 320, f"WAVE {before} CLEARED  +{C.RYO_PER_WAVE * before} ryo",
                               C.GOLD, size=40, life=2.0)
        w.update(dt)
        self.after_update(dt, w.events)
        w.events.clear()
        if self.practice_won is not None:
            self.practice_won += dt
        if self.practice_boss and (self.practice_won or 0) >= PRACTICE_WIN_DELAY or \
                self.practice_boss and w.game_over and w.dead_time >= GAME_OVER_DELAY:
            from .practice import PracticeScene
            self.app.change(PracticeScene(self.app))
            return
        if w.game_over and w.dead_time >= GAME_OVER_DELAY:
            from .gameover import GameOverScene
            earned = self.bank_earnings()
            self.app.change(GameOverScene(self.app, w.score, self.director.number if self.director else 0, earned))

    def bank_earnings(self):
        """Add this run's ryo to the saved profile (only once). Returns the amount."""
        earned = 0 if self.practice_boss else self.world.ryo_earned
        if not self.banked:
            self.banked = True
            self.app.profile.bank(earned)
        return earned

    def fresh(self):
        """A new copy of this scene for Restart."""
        if self.practice_boss:
            return GameScene(self.app, practice_boss=self.practice_boss)
        return type(self)(self.app)

    def on_quit(self):
        self.bank_earnings()

    def after_update(self, dt, events):
        """Hook for the tutorial."""

    # ------------------------------------------------------------------ draw
    def banner(self):
        d = self.director
        if d and d.banner:
            title = f"WAVE {d.number}"
            return (title, d.wave.label), d.timer
        return None, 0.0

    def draw(self, surf):
        self.bg.draw(self.canvas)
        self.world.draw(self.canvas)
        surf.fill(C.BLACK)
        surf.blit(self.canvas, self.world.shake_offset())
        banner, t = self.banner()
        self.hud.draw(surf, self.world, self.director.number if self.director else None, banner, t)
        if self.practice_boss:
            from ..ui import draw_text
            draw_text(surf, self.app.font(28), "BOSS PRACTICE  -  no ryo or high score", C.GREY,
                      midbottom=(C.SCREEN_W // 2, C.SCREEN_H - 8))
        self.draw_overlay(surf)

    def draw_overlay(self, surf):
        pass
