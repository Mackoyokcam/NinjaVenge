"""All in-play game state and the rules that connect entities together.

Scenes own a World; entities call back into it (world.on_kill, world.sfx.play ...)
instead of setting flags for main() to poll.
"""
import random
from collections import Counter

from . import config as C
from .assets import Sfx
from .entities import Bullet, Effects, Kunai, Ninja, make_enemy
from .scoring import ScoreKeeper
from .upgrades import Loadout, run_earnings


class World:
    def __init__(self, app, tutorial=False, loadout=None):
        self.app = app
        self.assets = app.assets
        self.sfx = Sfx(app.assets)
        self.tutorial = tutorial
        self.loadout = loadout or Loadout()
        self.player = Ninja(self.assets, x=C.SCREEN_W // 2, lane=0, loadout=self.loadout)
        self.enemies = []
        self.kunais = []
        self.bullets = []
        self.effects = Effects(app.font)
        self.score = ScoreKeeper()
        self.hearts = self.loadout.max_hearts
        self.kills = 0
        self.kills_by_kind = Counter()
        self.waves_cleared = 0
        self.events = set()        # tags raised since the scene last cleared them (tutorial)
        self._hitstop = 0.0
        self._shake = 0.0
        self.dead_time = 0.0

    # ------------------------------------------------------------------ spawning
    def spawn(self, spawn, wave):
        enemy = make_enemy(self.assets, spawn, wave)
        self.enemies.append(enemy)
        return enemy

    def spawn_kunai(self, x, y, facing):
        self.kunais.append(Kunai(self.assets, x, y, facing, self.loadout.kunai_speed))
        self.sfx.play("throw")

    def spawn_bullet(self, x, y, facing):
        self.bullets.append(Bullet(x, y, facing))
        self.effects.sparks(x, y, (255, 220, 120), 6)

    # ------------------------------------------------------------------ queries
    @property
    def alive_enemies(self):
        return sum(1 for e in self.enemies if e.counts_for_wave)

    @property
    def boss(self):
        return next((e for e in self.enemies if e.kind == "boss" and e.hittable), None)

    @property
    def ryo_earned(self):
        if self.tutorial:
            return 0
        return run_earnings(self.kills_by_kind, self.waves_cleared)

    @property
    def game_over(self):
        return not self.player.alive

    def shake_offset(self):
        if self._shake <= 0:
            return 0, 0
        s = int(self._shake)
        return random.randint(-s, s), random.randint(-s, s)

    def emit(self, tag):
        self.events.add(tag)

    # ------------------------------------------------------------------ feel
    def hitstop(self, t):
        self._hitstop = max(self._hitstop, t)

    def shake(self, amount):
        self._shake = max(self._shake, amount)

    # ------------------------------------------------------------------ rules
    def sword_strike(self, player):
        """Called every frame the blade is in its active window."""
        blade = player.sword_rect
        for e in self.enemies:
            if id(e) in player.swing_hits:
                continue
            if e.hittable and blade.colliderect(e.body_rect):
                player.swing_hits.add(id(e))
                e.on_sword(self, player.airborne)
            elif e.smashable and blade.colliderect(e.corpse_rect):
                player.swing_hits.add(id(e))
                e.smash(self)
        for b in self.bullets:
            if b.alive and not b.friendly and blade.colliderect(b.rect):
                b.reflect()
                self.sfx.play("dink")
                self.effects.sparks(b.x, b.y, (255, 240, 170), 10)
                pts = self.score.bonus(C.DEFLECT_BONUS)
                self.effects.text(b.x, b.y - 30, f"DEFLECT +{pts}", (255, 240, 170), size=22)
                self.emit("deflect")

    def on_hit(self, enemy):
        self.hitstop(C.HITSTOP_HIT)
        self.shake(C.SHAKE_HIT * 0.6)
        self.effects.sparks(enemy.x, enemy.y - 70 * enemy.scale, C.WHITE, 8)

    def on_kill(self, enemy, airborne):
        bonus = C.AIR_KILL_BONUS if airborne else 0
        pts = self.score.kill(C.POINTS[enemy.kind], bonus)
        self.kills += 1
        self.kills_by_kind[enemy.kind] += 1
        if not self.tutorial:
            self.effects.text(enemy.x, enemy.y - 118 * enemy.scale, f"+{C.RYO[enemy.kind]} ryo", C.WHITE, size=22)
        label = f"+{pts}" + ("  AIR!" if airborne else "")
        self.effects.text(enemy.x, enemy.y - 150 * enemy.scale, label, C.GOLD)
        mult = 1 + self.score.streak // C.COMBO_STEP
        if self.score.streak % C.COMBO_STEP == 0 and 1 < mult <= C.COMBO_MAX:
            self.effects.text(self.player.x, self.player.y - 190, f"COMBO x{mult}", C.ORANGE, size=34)
        self.effects.burst(enemy.x, enemy.y - 70 * enemy.scale, (200, 30, 40) if enemy.kind != "robot" else C.CYAN)
        heavy = enemy.kind == "boss"
        self.hitstop(C.HITSTOP_KILL * (3 if heavy else 1))
        self.shake(C.SHAKE_HIT * (3 if heavy else 1))
        self.emit(f"kill:{enemy.kind}")

    def on_smash(self, enemy):
        pts = self.score.bonus(C.SMASH_BONUS)
        cx, cy = enemy.corpse_rect.center
        self.sfx.play("punch")
        self.effects.burst(cx, cy, C.ORANGE, n=26, speed=420, size=5, life=0.7)
        self.effects.text(cx, cy - 60, f"SMASH +{pts}", C.ORANGE)
        self.hitstop(C.HITSTOP_HIT)
        self.shake(C.SHAKE_HIT)
        self.emit("smash")

    def damage_player(self, from_x):
        p = self.player
        if not p.vulnerable:
            return
        p.hurt(from_x)
        self.sfx.play("ugh")
        self.shake(C.SHAKE_HURT)
        self.hitstop(C.HITSTOP_KILL)
        self.effects.burst(p.x, p.y - 70, (200, 30, 40), n=10)
        self.emit("hurt")
        self._lose_hearts(1)

    def leak(self, enemy):
        edge_x = C.SCREEN_W - 60 if enemy.facing > 0 else 60
        self.sfx.play("ugh")
        self.effects.text(edge_x, enemy.y - 100, f"-{enemy.leak_cost} HEART" + ("S" if enemy.leak_cost > 1 else ""),
                          C.RED, size=30, life=1.4)
        self.shake(C.SHAKE_HURT * 0.6)
        self.emit("leak")
        self._lose_hearts(enemy.leak_cost)

    def _lose_hearts(self, n):
        self.score.break_combo()
        if self.tutorial:
            return  # the tutorial can't be lost
        self.hearts = max(0, self.hearts - n)
        if self.hearts == 0 and self.player.alive:
            self.player.die()
            self.sfx.play("game_over")
            self.assets.stop_music()
            for e in self.enemies:
                e.speed = 0

    # ------------------------------------------------------------------ update
    def update(self, dt):
        self.effects.update(dt)
        self._shake = max(0.0, self._shake - 60 * dt)
        if self._hitstop > 0:
            self._hitstop -= dt
            return
        if self.game_over:
            self.dead_time += dt

        self.player.update(dt, self)
        for e in self.enemies:
            e.update(dt, self)

        body = self.player.body_rect
        if self.player.alive:
            for e in self.enemies:
                if e.hittable and body.colliderect(e.body_rect):
                    e.touch_player(self, self.player)

        for k in self.kunais:
            k.update(dt)
            if not k.alive:
                continue
            # kunai fly straight through pumpkin corpses: only a slash can smash one
            for e in self.enemies:
                if e.hittable and k.rect.colliderect(e.body_rect):
                    e.on_projectile(self)
                    k.alive = False
                    break

        for b in self.bullets:
            b.update(dt)
            if not b.alive:
                continue
            if b.friendly:
                for e in self.enemies:
                    if e.hittable and b.rect.colliderect(e.body_rect):
                        b.alive = False
                        self.effects.text(e.x, e.y - 190 * e.scale, "RICOCHET!", C.CYAN, size=26)
                        self.emit("ricochet")
                        e.on_projectile(self)
                        break
            elif self.player.vulnerable and b.rect.colliderect(body):
                b.alive = False
                self.damage_player(b.x - b.facing * 100)

        self.kunais = [k for k in self.kunais if k.alive]
        self.bullets = [b for b in self.bullets if b.alive]
        self.enemies = [e for e in self.enemies if e.state != "gone"]

    # ------------------------------------------------------------------ draw
    def draw(self, surf):
        # upper lanes first so lower (closer) lanes overlap them
        for e in sorted(self.enemies, key=lambda e: e.y):
            e.draw(surf)
        self.player.draw(surf)
        for k in self.kunais:
            k.draw(surf)
        for b in self.bullets:
            b.draw(surf)
        self.effects.draw(surf)
