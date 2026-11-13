"""The player's saved progress: ryo balance and purchased upgrades."""
import json
import os

from . import config
from .upgrades import BY_KEY, loadout_from


class Profile:
    def __init__(self, path=None):
        self.path = path or config.PROFILE_PATH
        self.ryo = 0
        self.levels = {}
        self.enabled = {}
        self._load()

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        self.ryo = max(0, int(data.get("ryo", 0)))
        self.levels = {k: int(v) for k, v in data.get("levels", {}).items() if k in BY_KEY}
        self.enabled = {k: bool(v) for k, v in data.get("enabled", {}).items() if k in BY_KEY}

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"ryo": self.ryo, "levels": self.levels, "enabled": self.enabled}, f)
        except OSError:
            pass  # progress saving should never crash the game

    def level(self, key):
        return self.levels.get(key, 0)

    def is_enabled(self, key):
        return self.level(key) > 0 and self.enabled.get(key, True)

    def can_buy(self, key):
        cost = BY_KEY[key].cost(self.level(key))
        return cost is not None and self.ryo >= cost

    def buy(self, key):
        """Spend ryo on the next level. Returns True on success."""
        if not self.can_buy(key):
            return False
        self.ryo -= BY_KEY[key].cost(self.level(key))
        self.levels[key] = self.level(key) + 1
        self.save()
        return True

    def toggle(self, key):
        if BY_KEY[key].toggle and self.level(key) > 0:
            self.enabled[key] = not self.is_enabled(key)
            self.save()

    def bank(self, ryo):
        if ryo > 0:
            self.ryo += ryo
            self.save()

    def loadout(self):
        return loadout_from(self.levels, self.enabled)
