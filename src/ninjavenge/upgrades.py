"""Shop upgrades and the Loadout they produce. Pure logic, no pygame."""
from dataclasses import dataclass

from . import config as C


@dataclass(frozen=True)
class Upgrade:
    key: str
    name: str
    description: str
    costs: tuple          # cost of each level; len(costs) == max level
    toggle: bool = False  # owned upgrades that can be switched on/off (Shinobi Mode)

    @property
    def max_level(self):
        return len(self.costs)

    def cost(self, level):
        """Cost to go from `level` to `level + 1`, or None when maxed."""
        return self.costs[level] if level < self.max_level else None


UPGRADES = [
    Upgrade("kunai_speed", "Swift Kunai", "Kunai fly 20% faster per level.", (30, 60, 120)),
    Upgrade("quick_hands", "Quick Hands", "Kunai cooldown 20% shorter per level.", (40, 80, 160)),
    Upgrade("heavy_kunai", "Heavy Kunai", "Kunai staggers last 25% longer per level.", (40, 80, 160)),
    Upgrade("katana", "Sharpened Katana", "+0.5 katana damage per level.", (60, 120, 240)),
    Upgrade("swift_blade", "Swift Blade", "Shorter pause between katana swings.", (50, 100, 200)),
    Upgrade("fleet_feet", "Fleet Feet", "Run 10% faster per level.", (40, 90, 180)),
    Upgrade("hearts", "Extra Heart", "+1 maximum heart per level.", (100, 250)),
    Upgrade("shinobi", "Shinobi Mode", "Teleport between lanes in a flash. No jump attacks.", (150,), toggle=True),
]
BY_KEY = {u.key: u for u in UPGRADES}


@dataclass(frozen=True)
class Loadout:
    """Everything an upgrade can change, resolved into plain numbers for the game."""
    kunai_speed: float = C.KUNAI_SPEED
    kunai_cooldown: float = C.KUNAI_COOLDOWN
    sword_damage: float = 1.0
    max_hearts: int = C.PLAYER_MAX_HEARTS
    shinobi: bool = False
    stagger_mult: float = 1.0
    run_speed: float = C.PLAYER_SPEED
    attack_cooldown: float = C.ATTACK_COOLDOWN


def loadout_from(levels, enabled=None):
    """levels: {key: level}. enabled: {key: bool} for toggle upgrades (default on)."""
    enabled = enabled or {}
    lv = lambda k: max(0, min(int(levels.get(k, 0)), BY_KEY[k].max_level))
    return Loadout(
        kunai_speed=C.KUNAI_SPEED * (1 + 0.2 * lv("kunai_speed")),
        kunai_cooldown=C.KUNAI_COOLDOWN * (1 - 0.2 * lv("quick_hands")),
        sword_damage=1.0 + 0.5 * lv("katana"),
        max_hearts=C.PLAYER_MAX_HEARTS + lv("hearts"),
        shinobi=lv("shinobi") > 0 and enabled.get("shinobi", True),
        stagger_mult=1 + 0.25 * lv("heavy_kunai"),
        run_speed=C.PLAYER_SPEED * (1 + 0.1 * lv("fleet_feet")),
        attack_cooldown=C.ATTACK_COOLDOWN * (1 - lv("swift_blade") / 3),
    )


def run_earnings(kills_by_kind, waves_cleared):
    """Ryo earned from one run."""
    ryo = sum(C.RYO[k] * n for k, n in kills_by_kind.items())
    ryo += sum(C.RYO_PER_WAVE * w for w in range(1, waves_cleared + 1))
    return ryo
