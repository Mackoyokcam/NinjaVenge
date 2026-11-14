"""The tutorial is the real game scene with a script on top instead of waves."""
import pygame

from .. import config as C
from ..ui import draw_text
from ..waves import Spawn, Wave
from .game import GameScene

# (instruction, event that completes the step, enemy to spawn for the step)
STEPS = [
    ("Use LEFT / RIGHT to run.", "move", None),
    ("Press UP / DOWN to hop between lanes.", "switch", None),
    ("Press A to swing your katana.", "attack", None),
    ("Press S to throw a kunai.", "throw", None),
    ("Hop lanes and attack in mid-air for a jump attack.", "air_attack", None),
    ("A cowboy! He flashes '!' then shoots. Slash the bullet to send it back at him - or dodge and cut him down.",
     "kill:cowboy", "cowboy"),
    ("Robots are armored. Hit it with a kunai to stagger it, then slash it.", "kill:robot", "robot"),
    ("Jacks come back to life! Kill it, then SLASH the pumpkin before the ring closes. Kunai pass right through.",
     "smash", "jack"),
]

DONE_TEXT = "You're ready! Every enemy that gets past costs a heart. Press ENTER for the main menu."
TUTORIAL_WAVE = Wave(0, [], speed_mult=0.75, robot_hp=3, fire_mult=1.3, revive_time=4.5)


class TutorialScene(GameScene):
    tutorial = True

    def __init__(self, app, rng=None):
        super().__init__(app, rng)
        self.step = 0
        self.complete_t = 0.0   # >0 while showing "Nice!" before the next step
        self.respawn_t = 0.5

    @property
    def done(self):
        return self.step >= len(STEPS)

    def handle_event(self, event):
        if self.done and event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            from .menu import MenuScene
            self.app.change(MenuScene(self.app))
            return
        super().handle_event(event)

    def after_update(self, dt, events):
        if self.done:
            return
        text, goal, kind = STEPS[self.step]
        if self.complete_t > 0:
            self.complete_t -= dt
            if self.complete_t <= 0:
                self.step += 1
                self.respawn_t = 0.8
            return
        if goal in events:
            self.complete_t = 1.0
            self.world.effects.text(self.world.player.x, self.world.player.y - 180, "Nice!", C.GOLD, size=40)
            return
        # keep exactly one enemy of the step's kind around
        if kind and not any(e.kind == kind for e in self.world.enemies):
            self.respawn_t -= dt
            if self.respawn_t <= 0:
                p = self.world.player
                side = 1 if p.x < C.SCREEN_W / 2 else -1   # spawn on the far side
                self.world.spawn(Spawn(0, kind, p.lane, side), TUTORIAL_WAVE)
                self.respawn_t = 1.0

    def draw_overlay(self, surf):
        text = DONE_TEXT if self.done else STEPS[self.step][0]
        box = pygame.Rect(0, 0, C.SCREEN_W - 200, 60)
        box.midtop = (C.SCREEN_W // 2, 90)
        layer = pygame.Surface(box.size, pygame.SRCALPHA)
        layer.fill((0, 0, 0, 170))
        surf.blit(layer, box)
        pygame.draw.rect(surf, C.GOLD if self.complete_t > 0 else C.UI_ACCENT, box, 2, border_radius=6)
        draw_text(surf, self.app.font(32), text, C.WHITE, center=box.center)
        if not self.done:
            draw_text(surf, self.app.font(24), f"Step {self.step + 1} / {len(STEPS)}", C.GREY,
                      midtop=(box.centerx, box.bottom + 6))
