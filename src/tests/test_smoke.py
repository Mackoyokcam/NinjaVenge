"""Headless integration tests: drive real scenes with synthetic input."""
import os
import random
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from ninjavenge import config  # noqa: E402
from ninjavenge.app import App  # noqa: E402
from ninjavenge.entities.enemies import CORPSE, STAGGER, Jack, Robot, Cowboy  # noqa: E402
from ninjavenge.scenes.game import GameScene  # noqa: E402
from ninjavenge.scenes.gameover import GameOverScene  # noqa: E402
from ninjavenge.scenes.menu import MenuScene  # noqa: E402
from ninjavenge.scenes.pause import PauseScene  # noqa: E402
from ninjavenge.scenes.tutorial import STEPS, TutorialScene  # noqa: E402

DT = 1 / 60


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0)


class SmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls._old_save = config.SAVE_PATH, config.PROFILE_PATH
        config.SAVE_PATH = os.path.join(cls.tmp.name, "scores.json")
        config.PROFILE_PATH = os.path.join(cls.tmp.name, "profile.json")
        cls.app = App()

    @classmethod
    def tearDownClass(cls):
        config.SAVE_PATH, config.PROFILE_PATH = cls._old_save
        pygame.quit()
        cls.tmp.cleanup()

    def run_frames(self, n, events_fn=None):
        for i in range(n):
            self.app.step(DT, events_fn(i) if events_fn else [])

    def test_menu_starts_game_and_pause_resumes(self):
        app = self.app
        app.change(MenuScene(app))
        self.run_frames(5)
        app.step(DT, [key(pygame.K_RETURN)])   # "Start" is selected by default
        self.assertIsInstance(app.scene, GameScene)
        game = app.scene
        self.run_frames(10)
        app.step(DT, [key(pygame.K_ESCAPE)])
        self.assertIsInstance(app.scene, PauseScene)
        t = game.director.timer
        self.run_frames(30)
        self.assertEqual(game.director.timer, t, "game must be frozen while paused")
        app.step(DT, [key(pygame.K_ESCAPE)])
        self.assertIs(app.scene, game)

    def test_random_play_survives_and_reaches_game_over(self):
        app = self.app
        rng = random.Random(0)
        game = GameScene(app, rng=random.Random(0))
        app.change(game)
        keys = [pygame.K_UP, pygame.K_DOWN, pygame.K_a, pygame.K_s]
        game.read_movement = lambda: rng.choice((-1, 0, 1))
        for i in range(60 * 240):
            evs = [key(rng.choice(keys))] if rng.random() < 0.08 else []
            app.step(DT, evs)
            if isinstance(app.scene, GameOverScene):
                break
            if i == 60 * 120:
                game.world.hearts = 1   # speed things up
        self.assertIsInstance(app.scene, GameOverScene)
        self.assertGreater(game.world.kills, 0, "random mashing should kill something")
        self.run_frames(5)
        app.step(DT, [key(pygame.K_RETURN)])   # Retry
        self.assertIsInstance(app.scene, GameScene)

    def _game_with(self, enemy_cls, **kw):
        game = GameScene(self.app)
        self.app.change(game)
        game.director = None
        w = game.world
        w.player.x = 400
        e = enemy_cls(self.app.assets, 0, 1, **kw)  # spawn right, walk left
        e.x = 520
        e.speed = 0
        w.enemies.append(e)
        return game, w, e

    def test_each_enemy_has_its_own_death_sound(self):
        from ninjavenge.assets import SOUND_FILES
        from ninjavenge.entities import DinoBoss, KageBoss, KnightBoss
        heard = {}
        for cls, kw in ((Cowboy, {}), (Robot, {}), (Jack, {}), (KnightBoss, {"hp": 10}), (DinoBoss, {"hp": 10}),
                        (KageBoss, {"hp": 10})):
            game, w, e = self._game_with(cls, **kw)
            played = []
            w.sfx.play = played.append
            e.on_death_sound(w)
            heard[cls.__name__] = played[-1]
            self.assertIn(played[-1], SOUND_FILES)
        self.assertEqual(len(set(heard.values())), len(heard), heard)

    def test_sword_hits_multiple_enemies_once_per_swing(self):
        game, w, e1 = self._game_with(Cowboy)
        e2 = Cowboy(self.app.assets, 0, 1)
        e2.x, e2.speed = 470, 0
        e1.fire_cd = e2.fire_cd = 99
        w.enemies.append(e2)
        w.player.facing = 1
        self.app.step(DT, [key(pygame.K_a)])
        self.run_frames(40)
        self.assertEqual(w.kills, 2)

    def test_robot_kunai_staggers_then_sword_double_damage(self):
        game, w, robot = self._game_with(Robot, hp=4)
        w.player.facing = 1
        w.player.x = 300
        self.app.step(DT, [key(pygame.K_s)])
        for _ in range(60):
            self.app.step(DT, [])
            if robot.state == STAGGER:
                break
        self.assertEqual(robot.state, STAGGER)
        self.assertEqual(robot.hp, 4, "kunai must not damage robots")
        w.player.x = 430
        self.app.step(DT, [key(pygame.K_a)])   # pressed mid-throw: should be buffered
        self.run_frames(30)
        self.assertEqual(robot.hp, 2)

    def test_jack_revives_unless_smashed(self):
        game, w, jack = self._game_with(Jack, revive_time=0.5)
        jack.damage(w, 1)
        self.run_frames(int(60 * 0.8) + 10)
        self.assertEqual(jack.state, CORPSE)
        self.run_frames(40)
        self.assertEqual(jack.state, "walk", "jack should revive")
        self.assertEqual(jack.revives, 1)
        jack.speed = 0
        jack.damage(w, 1)
        self.run_frames(60)
        w.player.facing = 1
        self.app.step(DT, [key(pygame.K_a)])
        self.run_frames(30)
        self.assertNotIn(jack, w.enemies, "smashed pumpkin should be removed")

    def test_cowboy_shoots_player_in_lane(self):
        game, w, cb = self._game_with(Cowboy)
        cb.x = 900
        cb.fire_cd = 0
        hearts = w.hearts
        self.run_frames(120)
        self.assertEqual(w.hearts, hearts - 1)
        self.assertGreater(w.player.invuln, 0)

    def test_leak_costs_a_heart_and_keeps_other_enemies(self):
        game, w, cb = self._game_with(Cowboy)
        other = Robot(self.app.assets, 2, 1)
        other.speed = 0
        w.enemies.append(other)
        cb.x, cb.speed, cb.fire_cd = -config.SPAWN_MARGIN + 1, 200, 99
        self.run_frames(5)
        self.assertEqual(w.hearts, config.PLAYER_MAX_HEARTS - 1)
        self.assertIn(other, w.enemies)

    def test_can_run_while_throwing(self):
        game, w, cb = self._game_with(Cowboy)
        cb.x, cb.fire_cd = 1400, 99
        game.read_movement = lambda: 1
        self.run_frames(5)
        x0 = w.player.x
        self.app.step(DT, [key(pygame.K_s)])
        self.assertEqual(w.player.state.name, "THROW")
        self.run_frames(10)
        self.assertEqual(w.player.state.name, "THROW")
        self.assertGreater(w.player.x, x0 + 40, "Ren should keep running during a throw")
        self.assertEqual(len(w.kunais), 1)

    def test_jack_corpse_stays_visible_until_revive(self):
        game, w, jack = self._game_with(Jack, revive_time=3.0)
        jack.damage(w, 1)
        self.run_frames(int(60 * 2.8))
        self.assertEqual(jack.state, CORPSE)
        self.assertEqual(jack.corpse_alpha(), 255)
        self.assertIn(jack, w.enemies)

    def test_bosses_alternate_and_use_their_own_art(self):
        from ninjavenge.entities import DinoBoss, KageBoss, KnightBoss, boss_class
        self.assertIs(boss_class(5), KnightBoss)
        self.assertIs(boss_class(10), DinoBoss)
        self.assertIs(boss_class(15), KageBoss)
        self.assertIs(boss_class(20), KnightBoss)
        k = KnightBoss(self.app.assets, 0, 1, 10)
        self.assertNotEqual(k.run.right[0].get_size(), Robot(self.app.assets, 0, 1).run.right[0].get_size())

    def test_knight_swing_hits_unless_interrupted(self):
        from ninjavenge.entities import KnightBoss
        # uninterrupted: the swing lands
        game, w, knight = self._game_with(KnightBoss, hp=10)
        knight.x, knight.attack_cd = w.player.x + 130, 0
        self.run_frames(70)
        self.assertEqual(w.hearts, config.PLAYER_MAX_HEARTS - 1)
        # interrupted by a kunai during the wind-up
        game, w, knight = self._game_with(KnightBoss, hp=10)
        knight.x, knight.attack_cd = w.player.x + 160, 0
        w.player.facing = 1
        self.run_frames(2)
        self.assertEqual(knight.state, "attack")
        self.app.step(DT, [key(pygame.K_s)])
        self.run_frames(20)
        self.assertEqual(knight.state, STAGGER)
        self.run_frames(30)
        self.assertEqual(w.hearts, config.PLAYER_MAX_HEARTS)

    def test_dino_charges_and_can_be_interrupted(self):
        from ninjavenge.entities import DinoBoss
        game, w, dino = self._game_with(DinoBoss, hp=10)
        dino.x, dino.speed, dino.charge_cd = 1200, 0, 0
        w.player.x = 300
        self.run_frames(2)
        self.assertEqual(dino.state, "windup")
        self.run_frames(int(60 * config.DINO_WINDUP) + 2)
        self.assertEqual(dino.state, "charge")
        x0 = dino.x
        self.run_frames(20)
        self.assertLess(dino.x, x0 - 100, "charge should move fast")
        # interrupt
        game, w, dino = self._game_with(DinoBoss, hp=10)
        dino.x, dino.speed, dino.charge_cd = 900, 0, 0
        w.player.x, w.player.facing = 400, 1
        self.run_frames(2)
        self.app.step(DT, [key(pygame.K_s)])
        self.run_frames(30)
        self.assertEqual(dino.state, STAGGER)
        self.assertEqual(dino.hp, 10, "an interrupt staggers instead of damaging")

    # ------------------------------------------------------------ v3 features
    def setUp(self):
        from ninjavenge.profile import Profile
        self.app.profile = Profile()      # fresh, upgrade-free profile per test
        self.app.profile.levels, self.app.profile.enabled, self.app.profile.ryo = {}, {}, 0

    def test_kunai_passes_through_pumpkin_but_slash_smashes(self):
        game, w, jack = self._game_with(Jack, revive_time=5.0)
        jack.damage(w, 1)
        self.run_frames(60)
        self.assertTrue(jack.smashable)
        w.player.x, w.player.facing = 300, 1
        self.app.step(DT, [key(pygame.K_s)])
        self.run_frames(40)
        self.assertIn(jack, w.enemies, "kunai must not smash a pumpkin")
        self.assertTrue(jack.smashable)
        w.player.x = 460
        self.app.step(DT, [key(pygame.K_a)])
        self.run_frames(30)
        self.assertNotIn(jack, w.enemies)

    def _deflect_setup(self, target):
        from ninjavenge.entities import Bullet
        game, w, enemy = self._game_with(target)
        enemy.x = 900
        if hasattr(enemy, "fire_cd"):
            enemy.fire_cd = 99
        w.player.x, w.player.facing = 600, 1
        w.bullets.append(Bullet(700, w.player.y - 78, -1))   # incoming from the right
        self.app.step(DT, [key(pygame.K_a)])
        return game, w, enemy

    def test_deflected_bullet_flies_back_and_kills_cowboy(self):
        game, w, cb = self._deflect_setup(Cowboy)
        for _ in range(60):
            self.app.step(DT, [])
            if w.bullets and w.bullets[0].friendly:
                break
        self.assertTrue(w.bullets and w.bullets[0].friendly and w.bullets[0].facing == 1)
        self.run_frames(60)
        self.assertIn(cb.state, ("dying", "corpse"))
        self.assertEqual(w.hearts, config.PLAYER_MAX_HEARTS)

    def test_deflected_bullet_staggers_robot_without_damage(self):
        game, w, robot = self._deflect_setup(Robot)
        self.run_frames(60)
        self.assertEqual(robot.state, STAGGER)
        self.assertEqual(robot.hp, robot.max_hp)

    def test_shinobi_mode_teleports_fast_and_invisible(self):
        self.app.profile.levels = {"shinobi": 1}
        game = GameScene(self.app)
        self.app.change(game)
        game.director = None
        p = game.world.player
        self.app.step(DT, [key(pygame.K_UP)])
        self.assertTrue(p.teleporting)
        self.run_frames(int(60 * config.SHINOBI_SWITCH_TIME) + 2)
        self.assertEqual((p.lane, p.airborne), (1, False))
        # toggled off -> normal jump again
        self.app.profile.enabled = {"shinobi": False}
        game = GameScene(self.app)
        self.app.change(game)
        self.assertFalse(game.world.player.loadout.shinobi)

    def test_katana_upgrade_increases_damage(self):
        self.app.profile.levels = {"katana": 2}
        game, w, robot = self._game_with(Robot, hp=4)
        w.player.x, w.player.facing = 430, 1
        self.app.step(DT, [key(pygame.K_a)])
        self.run_frames(30)
        self.assertEqual(robot.hp, 2)

    def test_kunai_upgrades_apply(self):
        self.app.profile.levels = {"kunai_speed": 3, "quick_hands": 3, "hearts": 2}
        game = GameScene(self.app)
        self.app.change(game)
        w = game.world
        self.assertAlmostEqual(w.player.loadout.kunai_cooldown, config.KUNAI_COOLDOWN * 0.4)
        self.assertEqual(w.hearts, config.PLAYER_MAX_HEARTS + 2)
        self.app.step(DT, [key(pygame.K_s)])
        self.run_frames(15)
        self.assertAlmostEqual(w.kunais[0].speed, config.KUNAI_SPEED * 1.6)

    def test_ryo_is_banked_on_game_over_and_spent_in_shop(self):
        from ninjavenge.scenes.shop import ShopScene
        game, w, cb = self._game_with(Cowboy)
        cb.damage(w, 1)
        w.waves_cleared = 2
        expected = config.RYO["cowboy"] + config.RYO_PER_WAVE * (1 + 2)
        self.assertEqual(w.ryo_earned, expected)
        w.hearts = 1
        w.leak(cb)
        self.run_frames(60 * 3)
        self.assertIsInstance(self.app.scene, GameOverScene)
        self.assertEqual(self.app.profile.ryo, expected)
        game.on_quit()   # banking happens only once
        self.assertEqual(self.app.profile.ryo, expected)
        self.app.profile.ryo = 100
        self.app.push(ShopScene(self.app))
        self.app.step(DT, [key(pygame.K_RETURN)])   # first row: Swift Kunai, 30 ryo
        self.assertEqual(self.app.profile.level("kunai_speed"), 1)
        self.assertEqual(self.app.profile.ryo, 70)
        self.app.step(DT, [key(pygame.K_ESCAPE)])
        self.assertIsInstance(self.app.scene, GameOverScene)

    # ------------------------------------------------------------ v4 features
    def test_knight_turns_around_on_player_behind(self):
        from ninjavenge.entities import KnightBoss
        game, w, knight = self._game_with(KnightBoss, hp=10)   # walking left (facing -1)
        knight.x, knight.attack_cd = w.player.x - 120, 0         # Ren is behind him
        self.run_frames(2)
        self.assertEqual(knight.state, "attack")
        self.assertEqual(knight.facing, 1, "should turn to face Ren")
        self.run_frames(70)
        self.assertEqual(w.hearts, config.PLAYER_MAX_HEARTS - 1)
        self.assertEqual(knight.facing, -1, "turns back to the road after swinging")

    def test_staggered_knight_does_not_turn(self):
        from ninjavenge.entities import KnightBoss
        game, w, knight = self._game_with(KnightBoss, hp=10)
        knight.x, knight.attack_cd = w.player.x - 120, 0
        knight.state, knight.stagger_t = STAGGER, 5.0
        self.run_frames(30)
        self.assertEqual((knight.state, knight.facing), (STAGGER, -1))
        self.assertEqual(w.hearts, config.PLAYER_MAX_HEARTS)

    def test_katana_cooldown_and_swift_blade(self):
        game, w, cb = self._game_with(Cowboy)
        cb.x, cb.fire_cd = 1400, 99          # out of reach: no hit-stop
        p = w.player
        game.do_action("attack")
        self.run_frames(int(60 * config.ATTACK_TIME) + 2)
        self.assertFalse(p.attack_ready)
        self.assertFalse(game.do_action("attack"), "swing must wait for the cooldown")
        self.run_frames(int(60 * config.ATTACK_COOLDOWN) + 2)
        self.assertTrue(game.do_action("attack"))
        self.app.profile.levels = {"swift_blade": 3}
        game, w, cb = self._game_with(Cowboy)
        cb.x, cb.fire_cd = 1400, 99
        game.do_action("attack")
        self.run_frames(int(60 * config.ATTACK_TIME) + 2)
        self.assertTrue(w.player.attack_ready)

    def test_fleet_feet_runs_faster(self):
        def distance():
            game, w, _ = self._game_with(Cowboy)
            game.read_movement = lambda: -1
            x0 = w.player.x
            self.run_frames(30)
            return x0 - w.player.x
        base = distance()
        self.app.profile.levels = {"fleet_feet": 3}
        self.assertAlmostEqual(distance() / base, 1.3, places=1)

    def test_heavy_kunai_staggers_longer(self):
        self.app.profile.levels = {"heavy_kunai": 2}
        game, w, robot = self._game_with(Robot, hp=4)
        robot.on_projectile(w)
        self.assertAlmostEqual(robot.stagger_t, config.ROBOT_STAGGER * 1.5)

    def test_shinobi_teleport_effect(self):
        self.app.profile.levels = {"shinobi": 1}
        game = GameScene(self.app)
        self.app.change(game)
        game.director = None
        fx = game.world.effects
        y0 = game.world.player.y
        self.app.step(DT, [key(pygame.K_UP)])
        out, arrive = fx.ghosts
        self.assertEqual((out.mode, arrive.mode), ("out", "in"))
        self.assertEqual(arrive.rect.bottom - out.rect.bottom, config.LANE_FLOORS[1] - config.LANE_FLOORS[0])
        self.assertGreater(arrive.delay, 0, "reappears after vanishing")
        self.assertTrue(fx.streaks)
        self.run_frames(3)
        game.draw(self.app.screen)
        self.run_frames(40)
        self.assertEqual((fx.ghosts, fx.streaks), ([], []))
        self.assertEqual(game.world.player.y, config.LANE_FLOORS[1])
        self.assertNotEqual(y0, game.world.player.y)

    # ------------------------------------------------------------ v5 features
    def test_dino_tail_swipes_player_behind(self):
        from ninjavenge.entities import DinoBoss
        game, w, dino = self._game_with(DinoBoss, hp=10)   # walking left
        dino.x, dino.charge_cd, dino.tail_cd = w.player.x - 120, 99, 0   # Ren is behind him
        self.run_frames(2)
        self.assertEqual(dino.state, "tail")
        for _ in range(int(60 * config.DINO_TAIL_TIME) + 4):
            self.app.step(DT, [])
            game.draw(self.app.screen)            # rotated sprite + swoosh draw fine
        self.assertEqual(w.hearts, config.PLAYER_MAX_HEARTS - 1)
        self.assertEqual(dino.state, "walk")
        self.assertEqual(dino.facing, -1, "Rex never turns around, only his tail does")

    def test_dino_tail_out_of_range_and_interrupt(self):
        from ninjavenge.entities import DinoBoss
        game, w, dino = self._game_with(DinoBoss, hp=10)
        dino.x, dino.charge_cd, dino.tail_cd = w.player.x - config.DINO_TAIL_RANGE - 40, 99, 0
        self.run_frames(30)
        self.assertEqual((dino.state, w.hearts), ("walk", config.PLAYER_MAX_HEARTS))
        # a kunai into the coiling tail interrupts it
        game, w, dino = self._game_with(DinoBoss, hp=10)
        dino.x, dino.charge_cd, dino.tail_cd = w.player.x - 120, 99, 0
        self.run_frames(2)
        self.assertTrue(dino.tail_winding_up)
        dino.on_projectile(w)
        self.assertEqual(dino.state, STAGGER)
        self.run_frames(40)
        self.assertEqual(w.hearts, config.PLAYER_MAX_HEARTS)

    def test_territory_scenery_and_music_follow_the_waves(self):
        game = GameScene(self.app)
        self.app.change(game)
        music = self.app.assets.music
        self.run_frames(2)
        self.assertEqual((game.bg.theme, music.current), ("medieval", "intro"))
        d = game.director
        for n, theme, track in ((5, "medieval", "knight"), (6, "prehistoric", "after_knight"),
                                (10, "prehistoric", "dino"), (11, "night", "after_dino"),
                                (15, "night", "kage"), (16, "medieval", "after_kage")):
            d.number = n - 1
            d._next_wave()
            self.run_frames(2)
            self.assertEqual((game.bg.theme, music.current), (theme, track), n)
        self.assertIsNotNone(game.bg.old, "scenery cross-fades")
        game.draw(self.app.screen)
        self.run_frames(int(60 * game.bg.FADE) + 2)
        self.assertIsNone(game.bg.old)
        game.world.hearts = 1
        game.world._lose_hearts(1)
        self.assertIsNone(music.current, "music stops on death")

    def test_backgrounds_load_and_animate(self):
        from ninjavenge.ui import Background
        for theme in ("medieval", "prehistoric"):
            bg = Background(self.app.assets, theme)
            self.assertEqual(bg.theme, theme, "pre-composed backdrop should exist in data/bg")
            for _ in range(120):
                bg.update(DT)
            bg.draw(self.app.screen)
        self.assertTrue(bg.smoke, "the volcano smokes")
        self.assertEqual(Background(self.app.assets, "nope").theme, "night")

    def test_credits_screen_scrolls_and_closes(self):
        from ninjavenge.scenes.info import CreditsScene
        menu = MenuScene(self.app)
        self.app.change(menu)
        menu.credits()
        credits = self.app.scene
        self.assertIsInstance(credits, CreditsScene)
        self.run_frames(60)
        self.assertGreater(credits.scroll, 0, "auto-scrolls")
        self.app.step(DT, [key(pygame.K_UP)] * 50)
        self.assertEqual(credits.scroll, 0)
        credits.scroll = credits.max_scroll
        credits.draw(self.app.screen)
        self.app.step(DT, [key(pygame.K_ESCAPE)])
        self.assertIs(self.app.scene, menu)

    def test_in_game_credits_match_the_credits_file(self):
        import re
        from ninjavenge.credits import SECTIONS
        path = os.path.join(os.path.dirname(__file__), "..", "..", "CREDITS")
        with open(path, encoding="utf-8") as f:
            urls = set(re.findall(r"opengameart\.org/content/[\w-]+", f.read()))
        shown = {src for _, entries in SECTIONS for _, _, src in entries if src}
        self.assertEqual(urls, shown)

    # ------------------------------------------------------------------ Kage
    def _kage(self, hp=20):
        from ninjavenge.entities import KageBoss
        game, w, kage = self._game_with(KageBoss, hp=hp)
        self.assertEqual(kage.state, "blink", "she arrives by teleport")
        self.run_frames(int(60 * config.KAGE_BLINK_TIME) + 2)
        self.assertEqual(kage.state, "idle")
        return game, w, kage

    def _place(self, kage, w, dx):
        """Put Kage in Ren's lane, dx pixels from him, ready to act."""
        kage.lane, kage.y = w.player.lane, float(config.LANE_FLOORS[w.player.lane])
        kage.x = w.player.x + dx
        kage.state, kage.timer, kage.windup = "idle", 99, 0.0

    def test_kage_teleports_into_rens_lane(self):
        game, w, kage = self._kage()
        self.assertGreater(kage.max_hp, 0)
        self.assertEqual(kage.max_hp, round(20 * config.KAGE_HP_MULT))
        w.player.lane, w.player.y = 2, float(config.LANE_FLOORS[2])
        kage.timer = 0
        self.app.step(DT, [])
        self.assertEqual(kage.state, "blink")
        self.assertTrue(w.effects.ghosts, "teleport flicker")
        game.draw(self.app.screen)                     # shimmer where she'll land
        self.run_frames(int(60 * config.KAGE_BLINK_TIME) + 2)
        self.assertEqual(kage.lane, 2)
        self.assertGreaterEqual(abs(kage.x - w.player.x), config.KAGE_BLINK_DIST[0] - 1)
        self.assertIs(w.boss, kage, "boss bar stays up")

    def test_kage_shuriken_volley_hits_and_can_be_slashed_back(self):
        from ninjavenge.entities import Shuriken
        game, w, kage = self._kage()
        self._place(kage, w, 450)
        kage.state, kage.windup, kage.shots, kage.timer = "throw", 0.01, config.KAGE_THROW_COUNT, 0.0
        self.run_frames(3)
        self.assertTrue(any(isinstance(b, Shuriken) for b in w.bullets))
        self.run_frames(90)
        self.assertLess(w.hearts, config.PLAYER_MAX_HEARTS, "standing still eats a shuriken")
        self.assertIn(kage.state, ("recover", "idle", "blink", "throw", "slash", "dash"))
        # a shuriken slashed back staggers her and hurts
        self._place(kage, w, 300)
        hp = kage.hp
        star = Shuriken(kage.x - 40, kage.y - 80, 1)
        star.reflect()
        star.facing = 1 if kage.x > star.x else -1
        w.bullets.append(star)
        self.run_frames(4)
        self.assertEqual(kage.state, "stagger")
        self.assertEqual(kage.hp, hp - 2)

    def test_kage_kunai_blocked_unless_interrupt_or_opening(self):
        game, w, kage = self._kage()
        self._place(kage, w, 450)
        hp = kage.hp
        kage.on_projectile(w)
        self.assertEqual((kage.hp, kage.state), (hp, "idle"), "knocks kunai aside")
        kage.state, kage.windup = "throw", 0.3
        kage.on_projectile(w)
        self.assertEqual(kage.state, "stagger", "kunai during '!' interrupts")
        kage.state, kage.timer = "recover", 1.0
        kage.on_projectile(w)
        self.assertEqual(kage.hp, hp - 1)

    def test_kage_slash_and_dash(self):
        game, w, kage = self._kage()
        self._place(kage, w, 120)
        kage.timer = 0
        self.app.step(DT, [])
        self.assertEqual(kage.state, "slash", "close up she slashes")
        self.run_frames(60)
        self.assertEqual(w.hearts, config.PLAYER_MAX_HEARTS - 1)
        # dash straight through Ren
        game, w, kage = self._kage()
        self._place(kage, w, 450)
        kage.facing, kage.state, kage.windup, kage._struck = -1, "dash", 0.01, False
        self.run_frames(60)
        self.assertEqual(w.hearts, config.PLAYER_MAX_HEARTS - 1)
        self.assertLess(kage.x, w.player.x, "ended up on his other side")

    def test_kage_sword_hit_outside_opening_makes_her_blink(self):
        game, w, kage = self._kage()
        self._place(kage, w, 60)
        hp = kage.hp
        kage.on_sword(w, False)
        self.assertEqual((kage.hp, kage.state), (hp - 1, "blink"))
        self._place(kage, w, 60)
        kage.state, kage.timer = "recover", 1.0
        kage.on_sword(w, False)
        self.assertEqual(kage.state, "recover", "no escape during an opening")

    def test_kage_shadow_clones(self):
        game, w, kage = self._kage(hp=20)
        self._place(kage, w, 300)
        kage.state, kage.timer = "recover", 5
        while kage.hp > kage.max_hp * config.KAGE_CLONES_AT[0] + 1:
            kage.hp -= 1
        kage.on_projectile(w)                       # crosses the 50% line
        self.assertEqual(kage.state, "blink")
        self.run_frames(int(60 * config.KAGE_BLINK_TIME) + 10)
        clones = [e for e in w.enemies if e.kind == "clone"]
        self.assertEqual(len(clones), config.KAGE_CLONES)
        self.assertEqual(len({c.lane for c in clones} | {kage.lane}), config.KAGE_CLONES + 1, "one per lane")
        self.assertTrue(all(not c.counts_for_wave and not c.show_bar for c in clones))
        self.assertIs(w.boss, kage)
        game.draw(self.app.screen)
        clones[0].on_sword(w, False)
        self.assertEqual(clones[0].state, "gone", "a clone pops when hit")
        hp = kage.hp
        self.assertEqual(kage.hp, hp)
        kage.state = "recover"
        kage.damage(w, kage.hp)
        self.assertEqual(clones[1].state, "gone", "clones vanish with her")
        self.run_frames(120)
        self.assertEqual(w.alive_enemies, 0)

    # ------------------------------------------------------------------ Boss Practice
    def test_boss_practice_starts_at_the_boss_and_returns(self):
        from ninjavenge.entities import KageBoss
        from ninjavenge.scenes.practice import PracticeScene
        menu = MenuScene(self.app)
        self.app.change(menu)
        menu.practice()
        self.assertIsInstance(self.app.scene, PracticeScene)
        self.app.scene.fight("kage")
        game = self.app.scene
        self.assertEqual((game.director.number, game.practice_boss), (15, "kage"))
        self.assertEqual(game.stage(), ("night", "kage"))
        self.run_frames(int(60 * 2.5) + 5)
        self.assertIsInstance(game.world.boss, KageBoss)
        ryo = self.app.profile.ryo
        game.world.kills_by_kind["boss"] += 1
        for e in game.world.enemies:
            e.state = "gone"
        game.director._pending = []
        game.director.state = game.director.CLEARING
        self.run_frames(5)
        self.assertEqual(game.director.number, 15, "practice doesn't roll on to wave 16")
        game.draw(self.app.screen)
        self.run_frames(int(60 * 3.0) + 5)
        self.assertIsInstance(self.app.scene, PracticeScene)
        self.assertEqual(self.app.profile.ryo, ryo, "no ryo from practice")
        # losing also returns to the picker, without a high score
        self.app.scene.fight("knight")
        game = self.app.scene
        self.assertEqual(game.director.number, 5)
        game.world.hearts = 1
        game.world._lose_hearts(1)
        self.run_frames(int(60 * 2.5) + 5)
        self.assertIsInstance(self.app.scene, PracticeScene)

    def test_pause_restart_keeps_practice(self):
        from ninjavenge.scenes.practice import PracticeScene
        self.app.change(PracticeScene(self.app))
        self.app.scene.fight("dino")
        game = self.app.scene
        self.app.step(DT, [key(pygame.K_ESCAPE)])
        self.app.scene.restart()
        self.assertEqual(self.app.scene.practice_boss, "dino")

    def test_tutorial_plays_its_own_music(self):
        self.app.change(TutorialScene(self.app))
        self.run_frames(2)
        self.assertEqual(self.app.assets.music.current, "tutorial")

    def test_shop_grid_navigation(self):
        from ninjavenge.scenes.shop import ShopScene
        from ninjavenge.upgrades import UPGRADES
        shop = ShopScene(self.app)
        self.app.push(shop)
        self.app.step(DT, [key(pygame.K_RIGHT)])
        self.assertEqual(shop.selected, 1)
        self.app.step(DT, [key(pygame.K_DOWN)])
        self.assertEqual(shop.selected, 3)
        for _ in range(3):                       # 3 -> 5 -> 7 -> Back
            self.app.step(DT, [key(pygame.K_DOWN)])
        self.assertEqual(shop.selected, len(UPGRADES), "bottom of the grid lands on Back")
        self.assertTrue(all(r.bottom <= config.SCREEN_H - 40 for r in shop.rows), "shop fits on screen")
        self.app.step(DT, [key(pygame.K_RETURN)])
        self.assertIsNot(self.app.scene, shop)

    def test_knight_stagger_immunity_is_visible_and_temporary(self):
        from ninjavenge.entities import KnightBoss
        game, w, knight = self._game_with(KnightBoss, hp=10)
        knight.attack_cd = 99
        knight.on_projectile(w)
        self.assertEqual(knight.state, STAGGER)
        self.assertFalse(knight.stagger_immune_now)
        self.run_frames(int(60 * config.BOSS_STAGGER) + 3)
        self.assertEqual(knight.state, "walk")
        self.assertTrue(knight.stagger_immune_now, "glows right after recovering")
        w.events.clear()
        knight.on_projectile(w)
        self.assertNotEqual(knight.state, STAGGER)
        self.assertIn("immune", w.events)
        self.run_frames(int(60 * KnightBoss.recover_time) + 3)
        self.assertFalse(knight.stagger_immune_now)
        knight.on_projectile(w)
        self.assertEqual(knight.state, STAGGER)

    def test_immune_knight_can_still_be_interrupted(self):
        from ninjavenge.entities import KnightBoss
        game, w, knight = self._game_with(KnightBoss, hp=10)
        knight.stagger_immune = 1.0
        knight.x, knight.attack_cd = w.player.x + 130, 0
        self.run_frames(2)
        self.assertTrue(knight.winding_up)
        knight.on_projectile(w)
        self.assertEqual(knight.state, STAGGER, "timing the wind-up beats the immunity")

    def test_tutorial_can_be_completed(self):
        app = self.app
        tut = TutorialScene(app)
        app.change(tut)
        tut.read_movement = lambda: 1
        self.run_frames(80)                                   # move
        app.step(DT, [key(pygame.K_UP)]); self.run_frames(80)  # switch
        app.step(DT, [key(pygame.K_a)]); self.run_frames(80)   # attack
        app.step(DT, [key(pygame.K_s)]); self.run_frames(80)   # throw
        app.step(DT, [key(pygame.K_DOWN)]); app.step(DT, [key(pygame.K_a)]); self.run_frames(80)  # air attack
        self.assertEqual(tut.step, 5)
        tut.read_movement = lambda: 0
        # combat steps: cheat by killing/smashing the spawned enemy directly
        w = tut.world
        for _ in range(3):
            for _ in range(200):
                app.step(DT, [])
                if w.enemies:
                    break
            e = w.enemies[0]
            if isinstance(e, Robot):
                e.hp = 1
            e.damage(w, 1)
            if isinstance(e, Jack):
                self.run_frames(60)
                e.smash(w)
            self.run_frames(80)
            w.enemies.clear()
        self.assertTrue(tut.done, f"stuck on step {tut.step}: {STEPS[min(tut.step, len(STEPS)-1)][0]}")
        app.step(DT, [key(pygame.K_RETURN)])
        self.assertIsInstance(app.scene, MenuScene)


if __name__ == "__main__":
    unittest.main()
