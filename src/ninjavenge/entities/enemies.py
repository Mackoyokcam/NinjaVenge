"""Enemy types. Shared behaviour lives in Enemy; subclasses only add what's different."""
import math
import random

import pygame

from .. import config as C
from ..animation import Animation
from .sprite_utils import anchored_rect, glow_outline, tinted, with_alpha

WALK, AIM, STAGGER, DYING, CORPSE, GONE = "walk", "aim", "stagger", "dying", "corpse", "gone"


class Enemy:
    kind = "enemy"
    folder = ""
    run_time = 0.8
    leak_cost = 1
    scale = 1.0
    centered = False     # frames are centred on the body (prepared boss art)

    def __init__(self, assets, lane, side, speed, hp=1):
        self.lane = lane
        self.facing = 1 if side < 0 else -1
        self.x = float(-C.SPAWN_MARGIN if side < 0 else C.SCREEN_W + C.SPAWN_MARGIN)
        self.y = float(C.LANE_FLOORS[lane])
        self.speed = speed
        self.hp = self.max_hp = hp
        self.state = WALK
        self.run = Animation(assets.animation(f"{self.folder}/running", self.scale), self.run_time)
        self.die_anim = Animation(assets.animation(f"{self.folder}/dying", self.scale), 0.8, loop=False)
        self.anchor = self.run.right[0].get_width() / 2
        first = self.run.right[0]
        self.foot_pad = first.get_height() - first.get_bounding_rect().bottom  # transparent rows under the feet
        self.flash = 0.0
        self.corpse_t = 0.0
        self.stagger_t = 0.0

    # ------------------------------------------------------------------ queries
    @property
    def hittable(self):
        return self.state in (WALK, AIM, STAGGER)

    @property
    def smashable(self):
        return False

    @property
    def counts_for_wave(self):
        """Does this enemy stop the wave from ending?"""
        return self.state in (WALK, AIM, STAGGER, DYING)

    @property
    def body_rect(self):
        w, h = C.ENEMY_BODY
        r = pygame.Rect(0, 0, int(w * self.scale), int(h * self.scale))
        r.midbottom = (round(self.x), round(self.y))
        return r

    # ------------------------------------------------------------------ combat
    def damage(self, world, amount, airborne=False):
        self.hp -= amount
        self.flash = 0.1
        if self.hp <= 0:
            self.state = DYING
            self.die_anim.reset()
            world.on_kill(self, airborne)
            self.on_death_sound(world)
        else:
            world.on_hit(self)

    def on_death_sound(self, world):
        world.sfx.play("grunt")

    def on_sword(self, world, airborne):
        world.sfx.play("punch")
        self.damage(world, world.loadout.sword_damage, airborne)

    def on_projectile(self, world):
        """Hit by a kunai or a deflected bullet."""
        world.sfx.play("punch")
        self.damage(world, 1)

    def touch_player(self, world, player):
        """Called each frame the bodies overlap while this enemy is active."""

    # ------------------------------------------------------------------ update
    def update(self, dt, world):
        self.flash = max(0.0, self.flash - dt)
        if self.state == WALK:
            self.run.update(dt)
            self.advance(dt, self.speed, world)
            if self.state == WALK:
                self.think(dt, world)
        elif self.state == AIM:
            self.think(dt, world)
        elif self.state == STAGGER:
            self.stagger_t -= dt
            if self.stagger_t <= 0:
                self.state = WALK
        elif self.state == DYING:
            self.die_anim.update(dt)
            if self.die_anim.done:
                self.state = CORPSE
                self.corpse_t = 0.0
        elif self.state == CORPSE:
            self.corpse_t += dt
            self.update_corpse(dt, world)

    def advance(self, dt, speed, world):
        """Move forward; leaking off the far edge costs the player hearts."""
        self.x += self.facing * speed * dt
        if (self.facing > 0 and self.x > C.SCREEN_W + C.SPAWN_MARGIN) or \
           (self.facing < 0 and self.x < -C.SPAWN_MARGIN):
            self.state = GONE
            world.leak(self)

    def think(self, dt, world):
        """Per-type AI hook while walking/aiming."""

    def update_corpse(self, dt, world):
        if self.corpse_t >= C.CORPSE_FADE:
            self.state = GONE

    # ------------------------------------------------------------------ draw
    def frame(self):
        if self.state in (DYING, CORPSE):
            return self.die_anim.frame(self.facing)
        return self.run.frame(self.facing)

    def draw(self, surf):
        img = self.frame()
        if self.state == STAGGER:
            img = tinted(img, (160, 200, 255), "mult")
        if self.flash > 0:
            img = tinted(img, (180, 180, 180), "add")
        if self.state == CORPSE and self.corpse_alpha() < 255:
            img = with_alpha(img, self.corpse_alpha())
        anchor = img.get_width() / 2 if self.centered else self.anchor
        rect = anchored_rect(img, self.x, self.y + self.foot_pad, self.facing, anchor)
        if self.state == STAGGER:
            rect.x += random.randint(-2, 2)
        self.draw_underlay(surf, img, rect)
        surf.blit(img, rect)
        self.draw_overlay(surf, rect)

    def draw_underlay(self, surf, img, rect):
        """Drawn behind the sprite (auras, glows)."""

    def draw_overlay(self, surf, rect):
        pass

    def corpse_alpha(self):
        return 255 * (1 - self.corpse_t / C.CORPSE_FADE)


class Cowboy(Enemy):
    """Fast, fragile, and shoots down his lane after a telegraph."""
    kind = "cowboy"
    folder = "cowboy"
    run_time = 0.6

    def __init__(self, assets, lane, side, speed=C.COWBOY_SPEED, fire_mult=1.0):
        super().__init__(assets, lane, side, speed)
        self.fire_mult = fire_mult
        self.fire_cd = self._roll_cd() * 0.6
        self.aim_t = 0.0

    def _roll_cd(self):
        return random.uniform(*C.COWBOY_FIRE_COOLDOWN) * self.fire_mult

    def think(self, dt, world):
        p = world.player
        if self.state == WALK:
            self.fire_cd -= dt
            on_screen = 40 < self.x < C.SCREEN_W - 40
            in_front = (p.x - self.x) * self.facing > 60
            if self.fire_cd <= 0 and on_screen and p.alive and p.lane == self.lane and in_front:
                self.state = AIM
                self.aim_t = C.COWBOY_TELEGRAPH
        elif self.state == AIM:
            self.aim_t -= dt
            if self.aim_t <= 0:
                world.spawn_bullet(self.x + self.facing * 55, self.y - 78, self.facing)
                self.state = WALK
                self.fire_cd = self._roll_cd()

    def draw_overlay(self, surf, rect):
        if self.state == AIM:
            # blinking "!" telegraph above the head
            if int(self.aim_t * 16) % 2 == 0:
                x, y = self.x, rect.top - 18
                pygame.draw.polygon(surf, C.GOLD, [(x - 9, y - 26), (x + 9, y - 26), (x + 4, y - 4), (x - 4, y - 4)])
                pygame.draw.circle(surf, C.GOLD, (round(x), round(y + 6)), 5)


class Robot(Enemy):
    """Armored: kunai only stagger it; the sword hits twice as hard while staggered."""
    kind = "robot"
    folder = "robot"
    run_time = 0.9
    stagger_time = C.ROBOT_STAGGER
    recover_time = 0.0   # stagger immunity after recovering

    def __init__(self, assets, lane, side, speed=C.ROBOT_SPEED, hp=C.ROBOT_HP):
        super().__init__(assets, lane, side, speed, hp)
        self.stagger_immune = 0.0

    def on_projectile(self, world):
        world.sfx.play("dink")
        world.effects.sparks(self.x - self.facing * 10, self.y - 80 * self.scale, C.CYAN, 10)
        if self.stagger_immune > 0 and self.state != STAGGER:
            # armor just recovered: the hit glances off
            world.effects.sparks(self.x - self.facing * 10, self.y - 80 * self.scale, C.GOLD, 12)
            world.effects.text(self.x, self.y - 150 * self.scale, "IMMUNE", C.GOLD, size=26)
            world.emit("immune")
        elif self.state != STAGGER:
            self.state = STAGGER
            self.stagger_t = self.stagger_time * world.loadout.stagger_mult
            world.emit("stagger")
            world.effects.text(self.x, self.y - 150 * self.scale, "STAGGER", C.CYAN, size=26)

    def on_sword(self, world, airborne):
        world.sfx.play("punch")
        power = world.loadout.sword_damage
        self.damage(world, power * 2 if self.state == STAGGER else power, airborne)

    def on_death_sound(self, world):
        world.sfx.play("robot_dead")

    def update(self, dt, world):
        was_staggered = self.state == STAGGER
        self.stagger_immune = max(0.0, self.stagger_immune - dt)
        super().update(dt, world)
        if was_staggered and self.state == WALK:
            self.stagger_immune = self.recover_time

    def touch_player(self, world, player):
        if self.state == WALK:
            world.damage_player(self.x)

    @property
    def stagger_immune_now(self):
        return self.stagger_immune > 0 and self.state != STAGGER and self.hittable

    def draw_underlay(self, surf, img, rect):
        if not self.stagger_immune_now:
            return
        # pulsing gold glow = "can't be staggered right now"
        r = 7
        glow = glow_outline(img, (255, 200, 40), r)
        pulse = 0.75 + 0.25 * math.sin(self.stagger_immune * 18)
        fade = min(1.0, self.stagger_immune / 0.3)   # fades out as the immunity ends
        glow.set_alpha(int(255 * pulse * fade))
        surf.blit(glow, rect.move(-r, -r))

    def draw_overlay(self, surf, rect):
        if not self.hittable or self.max_hp <= 1:
            return
        # health pips
        n = self.max_hp
        size, gap = 9, 4
        total = n * size + (n - 1) * gap
        x0 = round(self.x - total / 2)
        y = rect.top - 14
        for i in range(n):
            r = pygame.Rect(x0 + i * (size + gap), y, size, size)
            pygame.draw.rect(surf, C.CYAN if i < self.hp else (50, 60, 70), r)
            pygame.draw.rect(surf, C.BLACK, r, 1)


class Jack(Enemy):
    """Comes back from the dead unless you smash the pumpkin."""
    kind = "jack"
    folder = "jack"
    run_time = 0.7

    def __init__(self, assets, lane, side, speed=C.JACK_SPEED, revive_time=C.JACK_REVIVE_TIME):
        super().__init__(assets, lane, side, speed)
        self.revive_time = revive_time
        self.revives = 0

    @property
    def smashable(self):
        return self.state in (DYING, CORPSE)

    @property
    def counts_for_wave(self):
        return self.state != GONE

    @property
    def corpse_rect(self):
        img = self.die_anim.frame(self.facing)
        r = anchored_rect(img, self.x, self.y + self.foot_pad, self.facing, self.anchor)
        return r.inflate(-30, -int(r.height * 0.45)).move(0, int(r.height * 0.2))

    def on_death_sound(self, world):
        world.sfx.play("pumpkin_dead")

    def corpse_alpha(self):
        return 255  # the body stays fully visible until it revives or is smashed

    def smash(self, world):
        self.state = GONE
        world.on_smash(self)

    def update_corpse(self, dt, world):
        if self.corpse_t >= self.revive_time:
            self.state = WALK
            self.hp = 1
            self.revives += 1
            self.speed *= C.JACK_REVIVE_SPEEDUP
            self.run.reset()
            world.sfx.play("laugh")
            world.effects.text(self.x, self.y - 160, "HA HA HA!", C.ORANGE, size=28)
            world.emit("revive")

    def draw_overlay(self, surf, rect):
        if self.state != CORPSE:
            return
        # pulsing ring that closes as the revive timer runs out
        cx, cy = self.corpse_rect.center
        left = 1 - self.corpse_t / self.revive_time
        pulse = 0.5 + 0.5 * math.sin(self.corpse_t * (6 + 10 * (1 - left)))
        radius = 52
        color = (255, int(110 + 100 * pulse), 30)
        arc_rect = pygame.Rect(0, 0, radius * 2, radius * 2)
        arc_rect.center = (cx, cy)
        pygame.draw.arc(surf, color, arc_rect, math.pi / 2, math.pi / 2 + 2 * math.pi * left, 4)
