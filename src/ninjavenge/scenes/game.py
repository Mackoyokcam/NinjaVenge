import pygame

from .. import config as C
from ..app import Scene
from ..ui import Background, Hud
from ..waves import WaveDirector
from ..world import World

LEFT_KEYS = (pygame.K_LEFT,)
RIGHT_KEYS = (pygame.K_RIGHT,)
UP_KEYS = (pygame.K_UP,)
DOWN_KEYS = (pygame.K_DOWN,)
ATTACK_KEYS = (pygame.K_a, pygame.K_j, pygame.K_z)
THROW_KEYS = (pygame.K_s, pygame.K_k, pygame.K_x)
PAUSE_KEYS = (pygame.K_ESCAPE, pygame.K_p, pygame.K_F1)

GAME_OVER_DELAY = 2.5
INPUT_BUFFER = 0.18  # seconds an early button press is remembered


class GameScene(Scene):
    tutorial = False

    def __init__(self, app, rng=None):
        super().__init__(app)
        self.world = World(app, tutorial=self.tutorial, loadout=app.profile.loadout())
        self.director = None if self.tutorial else WaveDirector(rng=rng)
        self.bg = Background()
        self.hud = Hud(app)
        self.canvas = pygame.Surface((C.SCREEN_W, C.SCREEN_H)).convert()
        self.buffered = None
        self.banked = False
        pygame.mouse.set_visible(False)
        app.assets.play_music()

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
            start_y = p.y
            if not p.try_switch_lane(1 if action == "up" else -1):
                return False
            w.emit("switch")
            if p.loadout.shinobi:
                # vanish in smoke and reappear in the next lane
                w.sfx.play("throw")
                target_y = C.LANE_FLOORS[p.lane + (1 if action == "up" else -1)]
                for y in (start_y, target_y):
                    w.effects.burst(p.x, y - 60, (190, 190, 210), n=16, speed=180, size=7, life=0.35)
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
            if self.director.number != before:
                w.waves_cleared = before
                w.effects.text(C.SCREEN_W // 2, 320, f"WAVE {before} CLEARED  +{C.RYO_PER_WAVE * before} ryo",
                               C.GOLD, size=40, life=2.0)
        w.update(dt)
        self.after_update(dt, w.events)
        w.events.clear()
        if w.game_over and w.dead_time >= GAME_OVER_DELAY:
            from .gameover import GameOverScene
            earned = self.bank_earnings()
            self.app.change(GameOverScene(self.app, w.score, self.director.number if self.director else 0, earned))

    def bank_earnings(self):
        """Add this run's ryo to the saved profile (only once). Returns the amount."""
        earned = self.world.ryo_earned
        if not self.banked:
            self.banked = True
            self.app.profile.bank(earned)
        return earned

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
        self.draw_overlay(surf)

    def draw_overlay(self, surf):
        pass
