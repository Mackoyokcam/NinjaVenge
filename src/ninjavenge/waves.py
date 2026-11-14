"""Wave definitions and the director that paces them. Pure logic, no pygame."""
import random
from dataclasses import dataclass, field

BOSS_EVERY = 5


@dataclass
class Spawn:
    time: float          # seconds after the wave starts
    kind: str            # "cowboy" | "robot" | "jack" | "boss"
    lane: int = None     # None = random
    side: int = None     # -1 spawn on the left moving right, +1 spawn right moving left, None = random


@dataclass
class Wave:
    number: int
    spawns: list
    speed_mult: float = 1.0
    robot_hp: int = 3
    boss_hp: int = 0
    fire_mult: float = 1.0   # <1 makes cowboys shoot more often
    revive_time: float = 3.5
    label: str = field(default="")


# Hand-authored opening waves; each one introduces a single idea.
def _handmade(n):
    S = Spawn
    if n == 1:
        return Wave(1, [S(0, "cowboy", 0), S(3, "cowboy", 1), S(6, "cowboy"), S(8.5, "cowboy")],
                    speed_mult=0.85, fire_mult=1.6, label="Cowboys shoot along their lane")
    if n == 2:
        return Wave(2, [S(0, "robot", 0), S(2.5, "cowboy"), S(5, "cowboy"), S(7, "robot"), S(9, "cowboy")],
                    speed_mult=0.9, fire_mult=1.4, label="Kunai staggers robots - then slash")
    if n == 3:
        return Wave(3, [S(0, "jack", 0), S(3, "jack"), S(5, "cowboy"), S(7, "jack"), S(8.5, "cowboy"),
                        S(10, "jack")],
                    speed_mult=0.95, fire_mult=1.3, label="Smash pumpkins before they revive")
    if n == 4:
        return Wave(4, [S(0, "cowboy"), S(1.2, "cowboy"), S(3, "robot"), S(4.5, "jack"), S(6, "jack"),
                        S(7, "cowboy"), S(8.5, "robot"), S(10, "cowboy"), S(11, "jack")],
                    speed_mult=1.0, fire_mult=1.15, label="")
    return None


def _boss_wave(n, rng):
    level = n // BOSS_EVERY
    spawns = [Spawn(0, "boss", rng.randrange(4))]
    t = 3.0
    for _ in range(min(2 + level * 2, 16)):
        spawns.append(Spawn(t, rng.choice(["cowboy", "jack"])))
        t += max(1.5, 3.5 - level * 0.4)
    return Wave(n, spawns, speed_mult=min(1.0 + 0.05 * level, 2.0), robot_hp=min(3 + level, 8),
                boss_hp=min(6 + 6 * level, 60), fire_mult=1.2, revive_time=3.5,
                label=("BOSS: Sir Clank - kunai him mid-swing to interrupt" if level % 2 == 1
                       else "BOSS: Rex - kunai him while he shakes to stop the charge"))


COSTS = {"cowboy": 1.0, "jack": 1.5, "robot": 2.0}


def _procedural(n, rng):
    budget = 6 + n * 1.5
    interval = max(0.55, 2.2 - n * 0.09)
    weights = {"cowboy": 5, "jack": 3 + min(n, 10) * 0.2, "robot": 2 + min(n, 12) * 0.25}
    spawns, t = [], 0.0
    while budget >= 1.0:
        kinds = [k for k in COSTS if COSTS[k] <= budget]
        kind = rng.choices(kinds, weights=[weights[k] for k in kinds])[0]
        budget -= COSTS[kind]
        spawns.append(Spawn(round(t, 2), kind))
        # occasional pairs keep the player switching lanes
        t += interval * (0.35 if rng.random() < 0.2 else rng.uniform(0.8, 1.2))
    return Wave(n, spawns,
                speed_mult=min(1.0 + 0.05 * (n - 4), 2.0),
                robot_hp=min(3 + (n - 4) // 3, 8),
                fire_mult=max(0.45, 1.1 - 0.05 * (n - 4)),
                revive_time=max(1.8, 3.5 - 0.1 * (n - 4)))


def build_wave(n, rng=random):
    if n % BOSS_EVERY == 0:
        return _boss_wave(n, rng)
    return _handmade(n) or _procedural(n, rng)


class WaveDirector:
    """INTRO (banner) -> SPAWNING -> CLEARING (wait for kills) -> next INTRO."""

    INTRO, SPAWNING, CLEARING = "intro", "spawning", "clearing"
    INTRO_TIME = 2.5

    def __init__(self, rng=None, start_wave=1):
        self.rng = rng or random.Random()
        self.number = start_wave - 1
        self.wave = None
        self.state = None
        self.timer = 0.0
        self._pending = []
        self._next_wave()

    def _next_wave(self):
        self.number += 1
        self.wave = build_wave(self.number, self.rng)
        self._pending = sorted(self.wave.spawns, key=lambda s: s.time)
        self.state = self.INTRO
        self.timer = 0.0

    def update(self, dt, alive_enemies):
        """Advance time; returns a list of Spawn to create this frame."""
        self.timer += dt
        out = []
        if self.state == self.INTRO:
            if self.timer >= self.INTRO_TIME:
                self.state, self.timer = self.SPAWNING, 0.0
        elif self.state == self.SPAWNING:
            while self._pending and self._pending[0].time <= self.timer:
                s = self._pending.pop(0)
                out.append(Spawn(s.time, s.kind,
                                 s.lane if s.lane is not None else self.rng.randrange(4),
                                 s.side if s.side is not None else self.rng.choice((-1, 1))))
            if not self._pending:
                self.state = self.CLEARING
        elif self.state == self.CLEARING:
            if alive_enemies == 0:
                self._next_wave()
        return out

    @property
    def banner(self):
        return self.state == self.INTRO
