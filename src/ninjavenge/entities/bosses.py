"""Boss enemies. Art: pzUH's CC0 GameArt2D packs (see CREDITS).

Shared rule: every boss telegraphs its big attack, and a kunai thrown during
the telegraph interrupts it and staggers the boss.
"""
import random

import pygame

from .. import config as C
from ..animation import Animation
from .enemies import STAGGER, WALK, Enemy, Robot

ATTACK, WINDUP, CHARGE = "attack", "windup", "charge"


def _draw_alert(surf, x, top, t):
    """Blinking '!' above a boss that is about to strike."""
    if int(t * 16) % 2:
        return
    y = top - 20
    pygame.draw.polygon(surf, C.RED, [(x - 11, y - 32), (x + 11, y - 32), (x + 5, y - 6), (x - 5, y - 6)])
    pygame.draw.circle(surf, C.RED, (round(x), round(y + 6)), 6)


class _BossMixin:
    kind = "boss"
    title = "BOSS"
    centered = True
    leak_cost = C.BOSS_LEAK_COST

    @property
    def body_rect(self):
        w, h = C.BOSS_BODY
        r = pygame.Rect(0, 0, w, h)
        r.midbottom = (round(self.x), round(self.y))
        return r

    def _player_ahead(self, world, max_dist):
        p = world.player
        ahead = (p.x - self.x) * self.facing
        return p.alive and p.lane == self.lane and 0 < ahead < max_dist

    def _interrupt(self, world):
        self.state = STAGGER
        self.stagger_t = C.BOSS_INTERRUPT_STAGGER
        world.sfx.play("dink")
        world.emit("stagger")
        world.effects.sparks(self.x, self.y - 120, C.CYAN, 14)
        world.effects.text(self.x, self.y - 250, "INTERRUPTED!", C.CYAN, size=32)
        world.shake(C.SHAKE_HIT)


class KnightBoss(_BossMixin, Robot):
    """Armored like a robot. Winds up a big sword swing when Ren is in front of him."""
    title = "SIR CLANK"
    folder = "boss/knight"
    run_time = 1.0
    stagger_time = C.BOSS_STAGGER
    recover_time = 1.5   # armor resets briefly after a stagger, so you can't lock him forever

    def __init__(self, assets, lane, side, hp):
        super().__init__(assets, lane, side, C.BOSS_SPEED, hp)
        self.attack_anim = Animation(assets.animation(f"{self.folder}/attack"), C.KNIGHT_ATTACK_TIME, loop=False)
        self.attack_cd = 1.0
        self._struck = False

    @property
    def hittable(self):
        return self.state in (WALK, STAGGER, ATTACK)

    @property
    def counts_for_wave(self):
        return super().counts_for_wave or self.state == ATTACK

    @property
    def winding_up(self):
        return self.state == ATTACK and self.attack_anim.progress < C.KNIGHT_SWING[0]

    @property
    def blade_rect(self):
        w, h = C.KNIGHT_REACH
        r = pygame.Rect(0, 0, w, h)
        r.bottom = round(self.y) - 10
        if self.facing > 0:
            r.left = round(self.x)
        else:
            r.right = round(self.x)
        return r

    def think(self, dt, world):
        self.attack_cd -= dt
        if self.attack_cd <= 0 and self._player_ahead(world, C.KNIGHT_REACH[0] + 20):
            self.state = ATTACK
            self.attack_anim.reset()
            self._struck = False

    def update(self, dt, world):
        if self.state == ATTACK:
            self.flash = max(0.0, self.flash - dt)
            self.attack_anim.update(dt)
            lo, hi = C.KNIGHT_SWING
            if not self._struck and lo <= self.attack_anim.progress <= hi:
                if world.player.body_rect.colliderect(self.blade_rect):
                    self._struck = True
                    world.damage_player(self.x)
            if self.attack_anim.done:
                self.state = WALK
                self.attack_cd = random.uniform(*C.KNIGHT_ATTACK_COOLDOWN)
            return
        super().update(dt, world)

    def on_projectile(self, world):
        if self.winding_up:
            self._interrupt(world)
            self.attack_cd = random.uniform(*C.KNIGHT_ATTACK_COOLDOWN)
        else:
            super().on_projectile(world)

    def frame(self):
        if self.state == ATTACK:
            return self.attack_anim.frame(self.facing)
        return super().frame()

    def draw_overlay(self, surf, rect):
        if self.winding_up:
            _draw_alert(surf, self.x, rect.top, self.attack_anim.time)


class DinoBoss(_BossMixin, Enemy):
    """Not armored, but tough. Stops, shakes, then charges down the lane."""
    title = "REX"
    folder = "boss/dino"
    run_time = 0.9

    def __init__(self, assets, lane, side, hp):
        super().__init__(assets, lane, side, C.DINO_SPEED, hp)
        self.charge_anim = Animation(assets.animation(f"{self.folder}/charge"), 0.45)
        self.charge_cd = random.uniform(*C.DINO_CHARGE_COOLDOWN) * 0.5
        self.timer = 0.0

    @property
    def hittable(self):
        return self.state in (WALK, STAGGER, WINDUP, CHARGE)

    @property
    def counts_for_wave(self):
        return super().counts_for_wave or self.state in (WINDUP, CHARGE)

    def think(self, dt, world):
        self.charge_cd -= dt
        on_screen = 120 < self.x < C.SCREEN_W - 120
        if self.charge_cd <= 0 and on_screen and self._player_ahead(world, C.SCREEN_W):
            self.state = WINDUP
            self.timer = C.DINO_WINDUP

    def update(self, dt, world):
        if self.state == WINDUP:
            self.flash = max(0.0, self.flash - dt)
            self.timer -= dt
            if self.timer <= 0:
                self.state = CHARGE
                self.timer = C.DINO_CHARGE_TIME
                self.charge_anim.reset()
                world.shake(C.SHAKE_HIT)
            return
        if self.state == CHARGE:
            self.flash = max(0.0, self.flash - dt)
            self.charge_anim.update(dt)
            self.timer -= dt
            self.advance(dt, C.DINO_CHARGE_SPEED, world)
            if self.state == CHARGE and self.timer <= 0:
                self.state = WALK
                self.charge_cd = random.uniform(*C.DINO_CHARGE_COOLDOWN)
            return
        super().update(dt, world)

    def on_projectile(self, world):
        if self.state == WINDUP:
            self._interrupt(world)
            self.charge_cd = random.uniform(*C.DINO_CHARGE_COOLDOWN)
        else:
            super().on_projectile(world)

    def on_sword(self, world, airborne):
        world.sfx.play("punch")
        power = world.loadout.sword_damage
        self.damage(world, power * 2 if self.state == STAGGER else power, airborne)

    def touch_player(self, world, player):
        if self.state in (WALK, CHARGE):
            world.damage_player(self.x)

    def frame(self):
        if self.state == CHARGE:
            return self.charge_anim.frame(self.facing)
        if self.state == WINDUP:
            return self.run.right[0] if self.facing > 0 else self.run.left[0]
        return super().frame()

    def draw(self, surf):
        if self.state == WINDUP:
            # shake in place while winding up
            ox = random.randint(-3, 3)
            self.x += ox
            super().draw(surf)
            self.x -= ox
        else:
            super().draw(surf)

    def draw_overlay(self, surf, rect):
        if self.state == WINDUP:
            _draw_alert(surf, self.x, rect.top, self.timer)
