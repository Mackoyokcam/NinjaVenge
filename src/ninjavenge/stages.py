"""Which territory, scenery and music each wave belongs to (pure logic).

Waves 1-5 are Sir Clank's medieval lands (boss: the knight on wave 5),
waves 6-10 are Rex's prehistoric jungle (dino on wave 10), waves 11-15 are
the ninja village at night, Kage's home (kage on wave 15), and then it repeats.
"""
from .waves import BOSS_EVERY, BOSS_ORDER, boss_name

MEDIEVAL, PREHISTORIC, VILLAGE = "medieval", "prehistoric", "night"
HOME = {"knight": MEDIEVAL, "dino": PREHISTORIC, "kage": VILLAGE}

__all__ = ["MEDIEVAL", "PREHISTORIC", "VILLAGE", "boss_name", "territory", "music_for"]


def territory(wave_number):
    """Each block of BOSS_EVERY waves belongs to the boss fought at its end."""
    block = (max(1, wave_number) - 1) // BOSS_EVERY
    return HOME[boss_name((block + 1) * BOSS_EVERY)]


def music_for(wave_number):
    if wave_number % BOSS_EVERY == 0:
        return boss_name(wave_number)
    if wave_number < BOSS_EVERY:
        return "intro"
    # the rounds after a boss: named for the boss you just beat
    return "after_" + boss_name(wave_number // BOSS_EVERY * BOSS_EVERY)
