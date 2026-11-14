"""Which territory, scenery and music each wave belongs to (pure logic).

Waves 1-5 are Sir Clank's medieval lands (boss: the knight on wave 5),
waves 6-10 are Rex's prehistoric jungle (boss: the dino on wave 10), and so on.
"""
from .waves import BOSS_EVERY

MEDIEVAL, PREHISTORIC = "medieval", "prehistoric"


def boss_name(wave_number):
    return "knight" if (wave_number // BOSS_EVERY) % 2 == 1 else "dino"


def territory(wave_number):
    block = (max(1, wave_number) - 1) // BOSS_EVERY
    return MEDIEVAL if block % 2 == 0 else PREHISTORIC


def music_for(wave_number):
    if wave_number % BOSS_EVERY == 0:
        return boss_name(wave_number)
    if wave_number < BOSS_EVERY:
        return "intro"
    # after a boss you move on into the next boss's land
    return "after_knight" if territory(wave_number) == PREHISTORIC else "after_dino"
