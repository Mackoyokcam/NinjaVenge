"""The player character, Ren."""
import math
from enum import Enum, auto

import pygame

from .. import config as C
from ..animation import Animation
from ..upgrades import Loadout
from .sprite_utils import anchored_rect, tinted


class State(Enum):
    IDLE = auto()
    RUN = auto()
    ATTACK = auto()
    THROW = auto()
    HURT = auto()
    DEAD = auto()


class Ninja:
    def __init__(self, assets, x=500, lane=0, loadout=None):
        self.loadout = loadout or Loadout()
        self.switch_time = C.SHINOBI_SWITCH_TIME if self.loadout.shinobi else C.LANE_SWITCH_TIME
        self.switch_arc = 0 if self.loadout.shinobi else C.LANE_SWITCH_ARC
        a = lambda name: assets.animation(f"ninja/right/{name}")
        self.anims = {
            "idle": Animation(a("idle"), 1.0),
            "run": Animation(a("running"), 0.6),
            "attack": Animation(a("attack"), C.ATTACK_TIME, loop=False),
            "throw": Animation(a("throwing"), C.THROW_TIME, loop=False),
            "jump": Animation(a("jumping"), C.LANE_SWITCH_TIME, loop=False),
            "jump_attack": Animation(a("jump_attack"), C.ATTACK_TIME, loop=False),
            "jump_throw": Animation(a("jump_throw"), C.THROW_TIME, loop=False),
            "dead": Animation(a("dead"), 1.0, loop=False),
        }
        self.x = float(x)
        self.lane = lane
        self.y = float(C.LANE_FLOORS[lane])
        self.facing = 1
        self.state = State.IDLE
        self.move_dir = 0

        # lane hop
        self.airborne = False
        self._hop_from = self._hop_to = lane
        self._hop_t = 0.0

        # actions
        self._released = False
        self._action_key = "attack"
        self.swing_hits = set()
        self.kunai_cd = 0.0
        self.attack_cd = 0.0

        # damage
        self.invuln = 0.0
        self._hurt_t = 0.0
        self._kb_vel = 0.0

    # ------------------------------------------------------------------ queries
    @property
    def alive(self):
        return self.state != State.DEAD

    @property
    def vulnerable(self):
        return self.alive and self.invuln <= 0

    @property
    def busy(self):
        return self.state in (State.ATTACK, State.THROW, State.HURT, State.DEAD)

    @property
    def teleporting(self):
        return self.airborne and self.loadout.shinobi

    @property
    def kunai_ready(self):
        return self.kunai_cd <= 0

    @property
    def body_rect(self):
        w, h = C.PLAYER_BODY
        r = pygame.Rect(0, 0, w, h)
        r.midbottom = (round(self.x), round(self.y))
        return r

    @property
    def sword_rect(self):
        w, h = C.SWORD_REACH
        r = pygame.Rect(0, 0, w, h)
        r.bottom = round(self.y) - 12
        if self.facing > 0:
            r.left = round(self.x) - 10
        else:
            r.right = round(self.x) + 10
        return r

    # ------------------------------------------------------------------ input
    def set_move(self, direction):
        self.move_dir = direction

    def try_switch_lane(self, delta):
        target = self.lane + delta
        if self.busy or self.airborne or not 0 <= target < len(C.LANE_FLOORS):
            return False
        self.airborne = True
        self._hop_from, self._hop_to, self._hop_t = self.lane, target, 0.0
        self.anims["jump"].reset()
        return True

    @property
    def attack_ready(self):
        return self.attack_cd <= 0

    def try_attack(self):
        if self.busy or not self.attack_ready:
            return False
        self.state = State.ATTACK
        self.swing_hits = set()
        self._action_key = "jump_attack" if self.airborne else "attack"
        self.anims[self._action_key].reset()
        return True

    def try_throw(self):
        if self.busy or not self.kunai_ready:
            return False
        self.state = State.THROW
        self._released = False
        self.kunai_cd = self.loadout.kunai_cooldown
        self._action_key = "jump_throw" if self.airborne else "throw"
        self.anims[self._action_key].reset()
        return True

    # ------------------------------------------------------------------ events
    def hurt(self, from_x):
        self.invuln = C.INVULN_TIME
        self._hurt_t = C.HURT_TIME
        self.state = State.HURT
        direction = 1 if self.x >= from_x else -1
        self._kb_vel = direction * C.KNOCKBACK / C.HURT_TIME * 1.5

    def die(self):
        self.state = State.DEAD
        self.anims["dead"].reset()

    # ------------------------------------------------------------------ update
    def update(self, dt, world):
        self.invuln = max(0.0, self.invuln - dt)
        self.kunai_cd = max(0.0, self.kunai_cd - dt)
        self.attack_cd = max(0.0, self.attack_cd - dt)

        if self.state == State.DEAD:
            self.anims["dead"].update(dt)
            self._update_hop(dt)  # finish falling into a lane
            return

        if self.state == State.HURT:
            self._hurt_t -= dt
            self.x += self._kb_vel * dt
            self._kb_vel *= 0.85
            if self._hurt_t <= 0:
                self.state = State.IDLE
        else:
            grounded_free = self.state in (State.IDLE, State.RUN)
            # sword swings root you in place; you can run while throwing and drift while hopping
            can_move = grounded_free or self.airborne or self.state == State.THROW
            if self.move_dir and can_move:
                self.x += self.move_dir * self.loadout.run_speed * dt
                if grounded_free:
                    self.facing = self.move_dir
                    if not self.airborne:
                        world.emit("move")
            if grounded_free:
                self.state = State.RUN if self.move_dir else State.IDLE

        self.x = max(30.0, min(C.SCREEN_W - 30.0, self.x))
        self._update_hop(dt)

        if self.state == State.ATTACK:
            anim = self.anims[self._action_key]
            anim.update(dt)
            lo, hi = C.ATTACK_ACTIVE
            if lo <= anim.progress <= hi:
                world.sword_strike(self)
            if anim.done:
                self.state = State.IDLE
                self.attack_cd = self.loadout.attack_cooldown
        elif self.state == State.THROW:
            anim = self.anims[self._action_key]
            anim.update(dt)
            if not self._released and anim.progress >= C.THROW_RELEASE:
                self._released = True
                world.spawn_kunai(self.x + self.facing * 30, self.y - 82, self.facing)
            if anim.done:
                self.state = State.IDLE
        else:
            self.anims["run" if self.state == State.RUN else "idle"].update(dt)

    def _update_hop(self, dt):
        if not self.airborne:
            self.y = float(C.LANE_FLOORS[self.lane])
            return
        self._hop_t += dt
        p = min(self._hop_t / self.switch_time, 1.0)
        y0, y1 = C.LANE_FLOORS[self._hop_from], C.LANE_FLOORS[self._hop_to]
        self.y = y0 + (y1 - y0) * p - math.sin(math.pi * p) * self.switch_arc
        self.anims["jump"].update(dt)
        # you "belong" to the lane you're closest to for enemy targeting
        self.lane = self._hop_to if p >= 0.5 else self._hop_from
        if p >= 1.0:
            self.airborne = False
            self.lane = self._hop_to
            self.y = float(y1)

    # ------------------------------------------------------------------ draw
    def current_frame(self):
        if self.state == State.DEAD:
            return self.anims["dead"].frame(self.facing)
        if self.state in (State.ATTACK, State.THROW):
            return self.anims[self._action_key].frame(self.facing)
        if self.airborne:
            return self.anims["jump"].frame(self.facing)
        if self.state == State.HURT:
            return self.anims["idle"].frame(self.facing)
        return self.anims["run" if self.state == State.RUN else "idle"].frame(self.facing)

    def draw(self, surf):
        if self.teleporting:
            return  # vanished in a puff of smoke
        if self.alive and self.invuln > 0 and self.state != State.HURT and int(self.invuln * 14) % 2:
            return  # blink while invulnerable
        img = self.current_frame()
        if self.state == State.HURT:
            img = tinted(img, (255, 90, 90), "mult")
        surf.blit(img, anchored_rect(img, self.x, self.y, self.facing, C.PLAYER_ANCHOR))
