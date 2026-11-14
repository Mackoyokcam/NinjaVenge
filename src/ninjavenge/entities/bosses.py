"""Boss enemies. Art: pzUH's CC0 GameArt2D packs (see CREDITS).

Shared rule: every boss telegraphs its big attack, and a kunai thrown during
the telegraph interrupts it and staggers the boss.
"""
import math
import random

import pygame

from .. import config as C
from ..animation import Animation
from .enemies import CORPSE, DYING, GONE, STAGGER, WALK, Enemy, Robot
from .sprite_utils import tinted, with_alpha

ATTACK, WINDUP, CHARGE, TAIL = "attack", "windup", "charge", "tail"


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
    def show_bar(self):
        """Show this boss's health bar on the HUD."""
        return self.hittable

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

    def _player_behind(self, world, max_dist):
        p = world.player
        behind = (self.x - p.x) * self.facing
        return p.alive and p.lane == self.lane and 0 < behind < max_dist

    def _interrupt(self, world):
        self.state = STAGGER
        self.stagger_t = C.BOSS_INTERRUPT_STAGGER * world.loadout.stagger_mult
        world.sfx.play("dink")
        world.emit("stagger")
        world.effects.sparks(self.x, self.y - 120, C.CYAN, 14)
        world.effects.text(self.x, self.y - 250, "INTERRUPTED!", C.CYAN, size=32)
        world.shake(C.SHAKE_HIT)


class KnightBoss(_BossMixin, Robot):
    """Armored like a robot. Winds up a big sword swing when Ren is in front of him,
    and turns around to swing at Ren if he lurks close behind (unless staggered)."""
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
        self._turned = False   # facing flipped for a swing behind him; restored afterwards

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
        if self.attack_cd > 0:
            return
        if self._player_ahead(world, C.KNIGHT_REACH[0] + 20):
            self._start_attack()
        elif self._player_behind(world, C.KNIGHT_TURN_RANGE):
            self.facing = -self.facing
            self._turned = True
            self._start_attack()

    def _start_attack(self):
        self.state = ATTACK
        self.attack_anim.reset()
        self._struck = False

    def update(self, dt, world):
        if self._turned and self.state != ATTACK:
            # swing finished, interrupted or staggered: face the road again
            self.facing = -self.facing
            self._turned = False
        if self.state == ATTACK:
            self.flash = max(0.0, self.flash - dt)
            self.stagger_immune = max(0.0, self.stagger_immune - dt)
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

    def on_death_sound(self, world):
        world.sfx.play("knight_dead")

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
    """Not armored, but tough. Stops, shakes, then charges down the lane.
    Lurking close behind him earns a tail swipe."""
    title = "REX"
    folder = "boss/dino"
    run_time = 0.9

    def __init__(self, assets, lane, side, hp):
        super().__init__(assets, lane, side, C.DINO_SPEED, hp)
        self.charge_anim = Animation(assets.animation(f"{self.folder}/charge"), 0.45)
        self.charge_cd = random.uniform(*C.DINO_CHARGE_COOLDOWN) * 0.5
        self.tail_cd = 0.8
        self.timer = 0.0
        self._struck = False

    @property
    def hittable(self):
        return self.state in (WALK, STAGGER, WINDUP, CHARGE, TAIL)

    @property
    def counts_for_wave(self):
        return super().counts_for_wave or self.state in (WINDUP, CHARGE, TAIL)

    @property
    def tail_progress(self):
        return 1 - self.timer / C.DINO_TAIL_TIME if self.state == TAIL else 0.0

    @property
    def tail_winding_up(self):
        return self.state == TAIL and self.tail_progress < C.DINO_TAIL_SWING[0]

    @property
    def tail_rect(self):
        w, h = C.DINO_TAIL_REACH
        r = pygame.Rect(0, 0, w, h)
        r.bottom = round(self.y) - 10
        if self.facing > 0:
            r.right = round(self.x) - 10
        else:
            r.left = round(self.x) + 10
        return r

    def think(self, dt, world):
        self.charge_cd -= dt
        self.tail_cd -= dt
        if self.tail_cd <= 0 and self._player_behind(world, C.DINO_TAIL_RANGE):
            self.state = TAIL
            self.timer = C.DINO_TAIL_TIME
            self._struck = False
            return
        on_screen = 120 < self.x < C.SCREEN_W - 120
        if self.charge_cd <= 0 and on_screen and self._player_ahead(world, C.SCREEN_W):
            self.state = WINDUP
            self.timer = C.DINO_WINDUP

    def update(self, dt, world):
        if self.state == TAIL:
            self.flash = max(0.0, self.flash - dt)
            was_winding = self.tail_winding_up
            self.timer -= dt
            lo, hi = C.DINO_TAIL_SWING
            if was_winding and not self.tail_winding_up:
                world.sfx.play("attack")       # whoosh
            if not self._struck and lo <= self.tail_progress <= hi:
                if world.player.body_rect.colliderect(self.tail_rect):
                    self._struck = True
                    world.damage_player(self.x)
            if self.timer <= 0:
                self.state = WALK
                self.tail_cd = random.uniform(*C.DINO_TAIL_COOLDOWN)
            return
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

    def on_death_sound(self, world):
        world.sfx.play("dino_dead")

    def on_projectile(self, world):
        if self.state == WINDUP:
            self._interrupt(world)
            self.charge_cd = random.uniform(*C.DINO_CHARGE_COOLDOWN)
        elif self.tail_winding_up:
            self._interrupt(world)
            self.tail_cd = random.uniform(*C.DINO_TAIL_COOLDOWN)
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
        if self.state in (WINDUP, TAIL):
            return self.run.right[0] if self.facing > 0 else self.run.left[0]
        return super().frame()

    def tail_angle(self):
        """Body tilt in degrees (positive = nose up) for the swipe: coil, whip, settle."""
        t, (lo, hi) = self.tail_progress, C.DINO_TAIL_SWING
        if t < lo:
            return 9 * math.sin(t / lo * math.pi / 2)          # rear back, tail down
        if t < hi:
            k = (t - lo) / (hi - lo)
            return 10 - 38 * math.sin(k * math.pi / 2)        # nose dips, tail whips up
        return -28 * (1 - (t - hi) / (1 - hi))               # settle back

    def draw(self, surf):
        if self.state == TAIL:
            self._draw_tail(surf)
            return
        if self.state == WINDUP:
            # shake in place while winding up
            ox = random.randint(-3, 3)
            self.x += ox
            super().draw(surf)
            self.x -= ox
        else:
            super().draw(surf)

    def _draw_tail(self, surf):
        img = self.frame()
        if self.flash > 0:
            img = tinted(img, (180, 180, 180), "add")
        angle = self.tail_angle() * self.facing
        rot = pygame.transform.rotate(img, angle)
        lunge = -self.facing * 14 * max(0.0, -self.tail_angle()) / 28   # hips shove back into the swipe
        base = img.get_rect(midbottom=(round(self.x + lunge), round(self.y + self.foot_pad)))
        surf.blit(rot, rot.get_rect(center=base.center))
        lo, hi = C.DINO_TAIL_SWING
        t = self.tail_progress
        if lo <= t <= hi + 0.12:
            self._draw_swoosh(surf, (t - lo) / (hi + 0.12 - lo))
        if self.tail_winding_up:
            _draw_alert(surf, self.x - self.facing * 70, base.top + 30, self.timer)

    def _draw_swoosh(self, surf, k):
        """White arc sweeping up behind Rex where the tail whips through."""
        cx, cy = self.x - self.facing * 30, self.y - 90      # Rex's hip
        radius = C.DINO_TAIL_REACH[0] - 30
        layer = pygame.Surface((radius * 2 + 20, radius * 2 + 20), pygame.SRCALPHA)
        c = radius + 10
        start, sweep = math.radians(215), math.radians(105) * min(1.0, k * 1.6)
        pts_out, pts_in = [], []
        for i in range(13):
            a = start - sweep * i / 12
            width = 44 * math.sin(math.pi * i / 12)
            pts_out.append((c + math.cos(a) * radius, c - math.sin(a) * radius))
            pts_in.append((c + math.cos(a) * (radius - width), c - math.sin(a) * (radius - width)))
        alpha = int(220 * (1 - max(0.0, k - 0.6) / 0.4))
        if len(pts_out) > 2:
            pygame.draw.polygon(layer, (255, 245, 220, alpha), pts_out + pts_in[::-1])
            pygame.draw.lines(layer, (255, 255, 255, alpha), False, pts_out, 3)
        if self.facing < 0:
            layer = pygame.transform.flip(layer, True, False)
        surf.blit(layer, (round(cx) - c, round(cy) - c))

    def draw_overlay(self, surf, rect):
        if self.state == WINDUP:
            _draw_alert(surf, self.x, rect.top, self.timer)


# Kage's states
IDLE, BLINK, THROW, SLASH, DASH, RECOVER = "idle", "blink", "throw", "slash", "dash", "recover"


class KageBoss(_BossMixin, Enemy):
    """Rival kunoichi. Doesn't walk the road: she hunts Ren. She blinks into his lane,
    throws shuriken volleys (slash them back to stagger her), slashes when he's close,
    or dashes through him. Low on health she splits into shadow clones.

    Openings: right after each move (RECOVER) or while staggered. A kunai during
    her '!' interrupts; otherwise she knocks kunai aside. A slash outside an opening
    still hurts her, but she blinks away right after."""
    title = "KAGE"
    folder = "boss/kage"
    run_time = 0.6

    def __init__(self, assets, lane, side, hp, owner=None):
        super().__init__(assets, lane, side, 0, 1 if owner is not None else max(1, round(hp * C.KAGE_HP_MULT)))
        a = assets.animation
        self.idle_anim = Animation(a(f"{self.folder}/idle"), 1.0)
        self.throw_anim = Animation(a(f"{self.folder}/throw"), C.KAGE_THROW_GAP, loop=False)
        self.attack_anim = Animation(a(f"{self.folder}/attack"), C.KAGE_SLASH_TIME, loop=False)
        self.slide_anim = Animation(a(f"{self.folder}/slide"), 0.4)
        self.owner = owner                  # set on shadow clones
        if owner is not None:
            self.kind = "clone"
        self.windup = 0.0
        self.shots = 0
        self.moves = 0                      # attacks since her last blink
        self.splits = list(C.KAGE_CLONES_AT)
        self.split_pending = False
        self._struck = False
        # she arrives by teleport, not by walking in
        self.x = float(260 if side < 0 else C.SCREEN_W - 260)
        self.state, self.timer, self.dest = BLINK, C.KAGE_BLINK_TIME, (lane, self.x)

    # ------------------------------------------------------------------ queries
    @property
    def is_clone(self):
        return self.owner is not None

    @property
    def body_rect(self):
        w, h = C.KAGE_BODY
        r = pygame.Rect(0, 0, w, h)
        r.midbottom = (round(self.x), round(self.y))
        return r

    @property
    def hittable(self):
        return self.state in (IDLE, THROW, SLASH, DASH, RECOVER, STAGGER)

    @property
    def counts_for_wave(self):
        return not self.is_clone and self.state not in (CORPSE, GONE)

    @property
    def show_bar(self):
        return not self.is_clone and self.state not in (DYING, CORPSE, GONE)

    @property
    def winding_up(self):
        return self.state in (THROW, SLASH, DASH) and self.windup > 0

    @property
    def open(self):
        """Openings where she takes hits without escaping."""
        return self.state in (RECOVER, STAGGER)

    @property
    def blade_rect(self):
        w, h = C.KAGE_SLASH_REACH
        r = pygame.Rect(0, 0, w, h)
        r.bottom = round(self.y) - 10
        if self.facing > 0:
            r.left = round(self.x)
        else:
            r.right = round(self.x)
        return r

    # ------------------------------------------------------------------ moves
    def _face(self, world):
        self.facing = 1 if world.player.x >= self.x else -1

    def _rect_at(self, lane, x):
        img = self.idle_anim.frame(self.facing)
        return img.get_rect(midbottom=(round(x), C.LANE_FLOORS[lane] + self.foot_pad))

    def _blink(self, world, lane=None, x=None):
        """Vanish, then reappear (by default in Ren's lane, a throw's distance away)."""
        p = world.player
        if lane is None:
            lane = p.lane
        if x is None:
            d = random.uniform(*C.KAGE_BLINK_DIST)
            sides = [s for s in (-1, 1) if 120 < p.x + s * d < C.SCREEN_W - 120]
            x = p.x + random.choice(sides or [1 if p.x < C.SCREEN_W / 2 else -1]) * d
            x = min(C.SCREEN_W - 120, max(120.0, x))
        world.effects.teleport(self.frame(), self._rect_at(self.lane, self.x), self._rect_at(lane, x),
                               arrive_delay=C.KAGE_BLINK_TIME)
        world.sfx.play("teleport")
        self.state, self.timer, self.dest = BLINK, C.KAGE_BLINK_TIME, (lane, x)
        self.windup = 0.0
        self.moves = 0

    def _arrive(self, world):
        self.lane, self.x = self.dest[0], float(self.dest[1])
        self.y = float(C.LANE_FLOORS[self.lane])
        self._face(world)
        self.state, self.timer = IDLE, random.uniform(*C.KAGE_IDLE) * 0.6
        if self.split_pending:
            self.split_pending = False
            self._split(world)

    def _split(self, world):
        """Shadow clones appear in other lanes; only the real Kage can be hurt."""
        lanes = [n for n in range(len(C.LANE_FLOORS)) if n != self.lane]
        random.shuffle(lanes)
        for lane in lanes[:C.KAGE_CLONES]:
            clone = KageBoss(world.assets, lane, 1, 1, owner=self)
            x = min(C.SCREEN_W - 140.0, max(140.0, self.x + random.uniform(-320, 320)))
            clone.x = x
            clone.dest = (lane, x)
            clone.timer = 0.05
            world.add_enemy(clone)
        world.effects.text(self.x, self.y - 210, "SHADOW CLONES!", C.CYAN, size=34)
        world.emit("clones")

    def _choose(self, world):
        p = world.player
        if not p.alive:
            self.timer = 1.0
            return
        dist = abs(p.x - self.x)
        if p.lane != self.lane or self.moves >= 2 or dist > 760:
            self._blink(world)
            return
        self._face(world)
        self.moves += 1
        self._struck = False
        if dist < C.KAGE_SLASH_RANGE:
            self.state, self.windup = SLASH, C.KAGE_SLASH_WINDUP
            self.attack_anim.reset()
        elif random.random() < 0.65:
            self.state, self.windup, self.shots, self.timer = THROW, C.KAGE_THROW_WINDUP, C.KAGE_THROW_COUNT, 0.0
        else:
            self.state, self.windup = DASH, C.KAGE_DASH_WINDUP

    def _recover(self, world):
        self.state, self.timer = RECOVER, C.KAGE_RECOVER
        self._face(world)

    # ------------------------------------------------------------------ combat
    def damage(self, world, amount, airborne=False):
        if self.is_clone:
            self._poof(world)
            return
        super().damage(world, amount, airborne)
        if self.state == DYING:
            for e in world.enemies + world._new_enemies:
                if getattr(e, "owner", None) is self and e.state != GONE:
                    e._poof(world)
            return
        if self.splits and self.hp <= self.max_hp * self.splits[0]:
            self.splits.pop(0)
            self.split_pending = True
            self._blink(world, lane=random.randrange(len(C.LANE_FLOORS)), x=C.SCREEN_W / 2)

    def _poof(self, world):
        here = self._rect_at(self.lane, self.x)
        world.effects.teleport(self.frame(), here, here)
        world.effects.text(self.x, self.y - 190, "FAKE!", C.GREY, size=28)
        world.sfx.play("teleport")
        self.state = GONE

    def on_death_sound(self, world):
        world.sfx.play("kage_dead")

    def on_sword(self, world, airborne):
        world.sfx.play("punch")
        was_open = self.open
        power = world.loadout.sword_damage
        self.damage(world, power * 2 if self.state == STAGGER else power, airborne)
        if not was_open and self.state not in (DYING, GONE, BLINK):
            self._blink(world)            # caught off guard: she escapes

    def on_projectile(self, world):
        if self.is_clone:
            self._poof(world)
        elif self.winding_up:
            self._interrupt(world)
        elif self.open:
            super().on_projectile(world)
        else:
            world.sfx.play("dink")         # knocks the kunai aside
            world.effects.sparks(self.x + self.facing * 30, self.y - 90, C.WHITE, 8)
            world.effects.text(self.x, self.y - 190, "BLOCKED", C.GREY, size=24)

    def on_ricochet(self, world):
        """Her own shuriken slashed back at her: always staggers."""
        if self.is_clone:
            self._poof(world)
            return
        world.sfx.play("punch")
        self.windup = 0.0
        self.state, self.stagger_t = STAGGER, C.KAGE_STAGGER * world.loadout.stagger_mult
        world.emit("stagger")
        world.effects.text(self.x, self.y - 160, "STAGGER", C.CYAN, size=26)
        self.damage(world, 2)

    # ------------------------------------------------------------------ update
    def update(self, dt, world):
        self.flash = max(0.0, self.flash - dt)
        if self.state in (DYING, CORPSE):
            super().update(dt, world)
            return
        if self.is_clone and self.owner.state in (DYING, CORPSE, GONE):
            self._poof(world)
            return
        self.idle_anim.update(dt)
        if self.state == BLINK:
            self.timer -= dt
            if self.timer <= 0:
                self._arrive(world)
        elif self.state == IDLE:
            self.timer -= dt
            if world.player.alive:
                self._face(world)
            if self.timer <= 0:
                self._choose(world)
        elif self.state == STAGGER:
            self.stagger_t -= dt
            if self.stagger_t <= 0:
                self.state, self.timer = IDLE, random.uniform(*C.KAGE_IDLE)
        elif self.state == RECOVER:
            self.timer -= dt
            if self.timer <= 0:
                self.state, self.timer = IDLE, random.uniform(*C.KAGE_IDLE) * 0.5
        elif self.windup > 0:
            self.windup -= dt
            if self.windup <= 0 and self.state in (DASH, SLASH):
                world.sfx.play("attack")
        elif self.state == THROW:
            self._update_throw(dt, world)
        elif self.state == SLASH:
            self._update_slash(dt, world)
        elif self.state == DASH:
            self._update_dash(dt, world)

    def _update_throw(self, dt, world):
        self.throw_anim.update(dt)
        self.timer -= dt
        if self.timer > 0:
            return
        if self.shots > 0:
            self.shots -= 1
            self.timer = C.KAGE_THROW_GAP
            self.throw_anim.reset()
            world.spawn_shuriken(self.x + self.facing * 50, self.y - 80, self.facing)
        else:
            self._recover(world)

    def _update_slash(self, dt, world):
        self.attack_anim.update(dt)
        if not self._struck and 0.3 <= self.attack_anim.progress <= 0.7:
            if world.player.body_rect.colliderect(self.blade_rect):
                self._struck = True
                world.damage_player(self.x)
        if self.attack_anim.done:
            self._recover(world)

    def _update_dash(self, dt, world):
        self.slide_anim.update(dt)
        self.x += self.facing * C.KAGE_DASH_SPEED * dt
        p = world.player
        if not self._struck and p.lane == self.lane and p.body_rect.colliderect(self.body_rect):
            self._struck = True
            world.damage_player(self.x)
        past = (self.x - p.x) * self.facing > 260
        if past or not 100 < self.x < C.SCREEN_W - 100:
            self.x = min(C.SCREEN_W - 100.0, max(100.0, self.x))
            self._recover(world)

    # ------------------------------------------------------------------ draw
    def frame(self):
        f = self.facing
        if self.state in (DYING, CORPSE):
            return self.die_anim.frame(f)
        if self.state == THROW:
            return self.throw_anim.frame(f)
        if self.state == SLASH:
            return self.attack_anim.frame(f)
        if self.state == DASH:
            return self.slide_anim.frame(f)
        return self.idle_anim.frame(f)

    def draw(self, surf):
        if self.state == BLINK:
            self._draw_shimmer(surf)
            return
        img = self.frame()
        if self.state == STAGGER:
            img = tinted(img, (160, 200, 255), "mult")
        if self.flash > 0:
            img = tinted(img, (180, 180, 180), "add")
        if self.state == CORPSE and self.corpse_alpha() < 255:
            img = with_alpha(img, self.corpse_alpha())
        elif self.is_clone:
            # the tell: clones are darker and a little see-through
            img = with_alpha(tinted(img, (120, 115, 150), "mult"), 215)
        rect = img.get_rect(midbottom=(round(self.x), round(self.y + self.foot_pad)))
        if self.state == STAGGER:
            rect.x += random.randint(-2, 2)
        surf.blit(img, rect)
        if self.winding_up:
            _draw_alert(surf, self.x, rect.top, self.windup)

    def _draw_shimmer(self, surf):
        """Where she's about to reappear: a faint, pulsing silhouette."""
        if int(self.timer * 24) % 2:
            return
        lane, x = self.dest
        k = 1 - self.timer / C.KAGE_BLINK_TIME
        img = tinted(self.idle_anim.frame(self.facing), (110, 190, 255), "add")
        img = with_alpha(img, int(40 + 90 * k))
        surf.blit(img, img.get_rect(midbottom=(round(x), C.LANE_FLOORS[lane] + self.foot_pad)))
