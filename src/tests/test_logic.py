"""Unit tests for the pure-logic modules. Run from src/: python -m unittest discover tests"""
import os
import random
import tempfile
import unittest

from ninjavenge import highscore
from ninjavenge.animation import Animation
from ninjavenge.scoring import ScoreKeeper
from ninjavenge.waves import BOSS_EVERY, WaveDirector, build_wave


class ScoreKeeperTest(unittest.TestCase):
    def test_multiplier_rises_every_step_and_caps(self):
        s = ScoreKeeper(step=5, max_mult=3)
        self.assertEqual(s.multiplier, 1)
        for _ in range(5):
            s.kill(100)
        self.assertEqual(s.multiplier, 2)
        for _ in range(50):
            s.kill(100)
        self.assertEqual(s.multiplier, 3)
        self.assertEqual(s.streak_progress, 1.0)

    def test_kill_points_use_multiplier_before_increment(self):
        s = ScoreKeeper(step=2, max_mult=5)
        self.assertEqual(s.kill(100), 100)   # streak 0 -> x1
        self.assertEqual(s.kill(100), 100)   # streak 1 -> x1
        self.assertEqual(s.kill(100), 200)   # streak 2 -> x2
        self.assertEqual(s.kill(100, bonus=50), 300)
        self.assertEqual(s.score, 700)

    def test_break_combo_resets_streak_but_keeps_best(self):
        s = ScoreKeeper(step=2)
        for _ in range(4):
            s.kill(10)
        s.break_combo()
        self.assertEqual(s.multiplier, 1)
        self.assertEqual(s.best_streak, 4)

    def test_bonus_does_not_count_toward_streak(self):
        s = ScoreKeeper(step=2)
        s.bonus(10)
        self.assertEqual(s.streak, 0)
        self.assertEqual(s.score, 10)


class WaveTest(unittest.TestCase):
    def test_every_fifth_wave_is_a_boss(self):
        rng = random.Random(1)
        for n in range(1, 31):
            kinds = [s.kind for s in build_wave(n, rng).spawns]
            self.assertEqual("boss" in kinds, n % BOSS_EVERY == 0, n)

    def test_waves_get_bigger(self):
        rng = random.Random(2)
        sizes = [len(build_wave(n, rng).spawns) for n in (6, 16, 26)]
        self.assertLess(sizes[0], sizes[2])

    def test_procedural_stats_are_capped(self):
        for n in (200, 201):  # boss and regular
            w = build_wave(n, random.Random(3))
            self.assertLessEqual(w.speed_mult, 2.0)
            self.assertLessEqual(w.robot_hp, 8)
            self.assertGreaterEqual(w.fire_mult, 0.45)

    def test_director_cycle(self):
        d = WaveDirector(rng=random.Random(4))
        self.assertEqual((d.number, d.state), (1, d.INTRO))
        self.assertEqual(d.update(d.INTRO_TIME + 0.01, 0), [])
        self.assertEqual(d.state, d.SPAWNING)
        spawned = []
        for _ in range(2000):
            spawned += d.update(0.05, alive_enemies=5)
            if d.state == d.CLEARING:
                break
        self.assertEqual(len(spawned), len(build_wave(1).spawns))
        self.assertTrue(all(s.lane in range(4) and s.side in (-1, 1) for s in spawned))
        d.update(0.05, alive_enemies=1)
        self.assertEqual(d.number, 1, "wave must not end while enemies are alive")
        d.update(0.05, alive_enemies=0)
        self.assertEqual((d.number, d.state), (2, d.INTRO))


class AnimationTest(unittest.TestCase):
    def test_loop_and_one_shot(self):
        frames = (list("abcd"), list("ABCD"))
        loop = Animation(frames, 1.0)
        loop.update(0.3)
        self.assertEqual(loop.frame(1), "b")
        self.assertEqual(loop.frame(-1), "B")
        loop.update(1.0)
        self.assertEqual(loop.frame(1), "b")
        once = Animation(frames, 1.0, loop=False)
        once.update(5)
        self.assertTrue(once.done)
        self.assertEqual(once.frame(1), "d")


class HighScoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "sub", "scores.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_missing_or_corrupt_file_is_empty(self):
        self.assertEqual(highscore.load(self.path), [])
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w") as f:
            f.write("{not json")
        self.assertEqual(highscore.load(self.path), [])

    def test_submit_keeps_top_entries_sorted(self):
        for s in (50, 300, 100, 400, 200, 10):
            highscore.submit(s, 1, self.path)
        table = highscore.load(self.path)
        self.assertEqual([e["score"] for e in table], [400, 300, 200, 100, 50])
        _, rank = highscore.submit(250, 3, self.path)
        self.assertEqual(rank, 2)
        _, rank = highscore.submit(1, 1, self.path)
        self.assertIsNone(rank)
        self.assertEqual(highscore.best(self.path), 400)


class UpgradeTest(unittest.TestCase):
    def test_loadout_math(self):
        from ninjavenge import config as C
        from ninjavenge.upgrades import loadout_from
        base = loadout_from({})
        self.assertEqual((base.sword_damage, base.max_hearts, base.shinobi), (1.0, C.PLAYER_MAX_HEARTS, False))
        full = loadout_from({"kunai_speed": 9, "quick_hands": 3, "katana": 3, "hearts": 2, "shinobi": 1})
        self.assertAlmostEqual(full.kunai_speed, C.KUNAI_SPEED * 1.6)   # clamped to max level 3
        self.assertAlmostEqual(full.kunai_cooldown, C.KUNAI_COOLDOWN * 0.4)
        self.assertEqual(full.sword_damage, 2.5)
        self.assertTrue(full.shinobi)
        self.assertFalse(loadout_from({"shinobi": 1}, {"shinobi": False}).shinobi)
        more = loadout_from({"heavy_kunai": 3, "fleet_feet": 3, "swift_blade": 3})
        self.assertAlmostEqual(more.stagger_mult, 1.75)
        self.assertAlmostEqual(more.run_speed, C.PLAYER_SPEED * 1.3)
        self.assertAlmostEqual(more.attack_cooldown, 0.0)
        self.assertAlmostEqual(base.attack_cooldown, C.ATTACK_COOLDOWN)

    def test_run_earnings(self):
        from ninjavenge import config as C
        from ninjavenge.upgrades import run_earnings
        self.assertEqual(run_earnings({}, 0), 0)
        self.assertEqual(run_earnings({"cowboy": 3, "boss": 1}, 3),
                         3 * C.RYO["cowboy"] + C.RYO["boss"] + C.RYO_PER_WAVE * 6)


class ProfileTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "p", "profile.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_buy_toggle_bank_and_persist(self):
        from ninjavenge.profile import Profile
        p = Profile(self.path)
        self.assertFalse(p.buy("kunai_speed"))
        p.bank(200)
        self.assertTrue(p.buy("kunai_speed"))       # 30
        self.assertTrue(p.buy("shinobi"))           # 150
        self.assertFalse(p.buy("shinobi"), "single-level upgrade can't be bought twice")
        self.assertEqual(p.ryo, 20)
        p.toggle("shinobi")
        q = Profile(self.path)
        self.assertEqual((q.ryo, q.level("kunai_speed"), q.is_enabled("shinobi")), (20, 1, False))
        self.assertFalse(q.loadout().shinobi)

    def test_corrupt_profile_starts_fresh(self):
        from ninjavenge.profile import Profile
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w") as f:
            f.write("[1, 2")
        self.assertEqual(Profile(self.path).ryo, 0)


if __name__ == "__main__":
    unittest.main()
