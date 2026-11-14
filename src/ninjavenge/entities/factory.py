from .. import config as C
from ..stages import boss_name
from .bosses import DinoBoss, KnightBoss
from .enemies import Cowboy, Jack, Robot


def boss_class(wave_number):
    """Bosses alternate: knight on waves 5, 15, 25...; dino on 10, 20, 30..."""
    return KnightBoss if boss_name(wave_number) == "knight" else DinoBoss


def make_enemy(assets, spawn, wave):
    """Build an enemy from a waves.Spawn + waves.Wave stats."""
    lane, side, m = spawn.lane, spawn.side, wave.speed_mult
    if spawn.kind == "cowboy":
        return Cowboy(assets, lane, side, C.COWBOY_SPEED * m, wave.fire_mult)
    if spawn.kind == "robot":
        return Robot(assets, lane, side, C.ROBOT_SPEED * m, wave.robot_hp)
    if spawn.kind == "jack":
        return Jack(assets, lane, side, C.JACK_SPEED * m, wave.revive_time)
    if spawn.kind == "boss":
        return boss_class(wave.number)(assets, lane, side, wave.boss_hp)
    raise ValueError(spawn.kind)
