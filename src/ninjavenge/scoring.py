"""Score + combo multiplier. Pure logic, no pygame."""
from . import config


class ScoreKeeper:
    def __init__(self, step=config.COMBO_STEP, max_mult=config.COMBO_MAX):
        self.step = step
        self.max_mult = max_mult
        self.score = 0
        self.streak = 0
        self.best_streak = 0

    @property
    def multiplier(self):
        return min(1 + self.streak // self.step, self.max_mult)

    @property
    def streak_progress(self):
        """0..1 progress toward the next multiplier level (1.0 when maxed)."""
        if self.multiplier >= self.max_mult:
            return 1.0
        return (self.streak % self.step) / self.step

    def kill(self, base_points, bonus=0):
        """Register a kill; returns the points awarded."""
        points = (base_points + bonus) * self.multiplier
        self.score += points
        self.streak += 1
        self.best_streak = max(self.best_streak, self.streak)
        return points

    def bonus(self, points):
        """Points that don't count toward the streak (deflects, smashes)."""
        points *= self.multiplier
        self.score += points
        return points

    def break_combo(self):
        self.streak = 0
