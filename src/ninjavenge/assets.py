"""Loads every image and sound exactly once and caches it."""
import glob
import os
import re

import pygame

from . import config


def _natural_key(path):
    """Sort 'Run (10).png' after 'Run (9).png'."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", os.path.basename(path))]


class _SilentSound:
    def play(self, *args, **kwargs):
        pass

    def set_volume(self, *args):
        pass


class Assets:
    def __init__(self, data_dir=config.DATA_DIR):
        self.data_dir = data_dir
        self._images = {}
        self._animations = {}
        self._sounds = {}
        self.audio = bool(pygame.mixer and pygame.mixer.get_init())
        self.music = Music(self)

    def path(self, *parts):
        return os.path.join(self.data_dir, *parts)

    def image(self, name, scale=1.0):
        key = (name, scale)
        if key not in self._images:
            surf = pygame.image.load(self.path(name)).convert_alpha()
            if scale != 1.0:
                w, h = surf.get_size()
                surf = pygame.transform.smoothscale(surf, (int(w * scale), int(h * scale)))
            self._images[key] = surf
        return self._images[key]

    def animation(self, folder, scale=1.0):
        """Return (right_frames, left_frames) for every PNG in a folder.

        Left-facing frames are pre-flipped once here instead of every frame.
        """
        key = (folder, scale)
        if key not in self._animations:
            files = sorted(glob.glob(self.path(folder, "*.png")), key=_natural_key)
            if not files:
                raise FileNotFoundError(f"No frames in {self.path(folder)}")
            right = []
            for f in files:
                surf = pygame.image.load(f).convert_alpha()
                if scale != 1.0:
                    w, h = surf.get_size()
                    surf = pygame.transform.smoothscale(surf, (int(w * scale), int(h * scale)))
                right.append(surf)
            left = [pygame.transform.flip(s, True, False) for s in right]
            self._animations[key] = (right, left)
        return self._animations[key]

    def sound(self, name, volume=1.0):
        if name not in self._sounds:
            if not self.audio:
                self._sounds[name] = _SilentSound()
            else:
                snd = pygame.mixer.Sound(self.path(name))
                snd.set_volume(volume)
                self._sounds[name] = snd
        return self._sounds[name]

    def play(self, name):
        self.sound(name).play()



SOUND_FILES = {
    "punch": "punch.wav",
    "attack": "attack.wav",
    "throw": "throw.wav",
    "jump": "jump.wav",
    "dink": "dink.wav",
    "robot_dead": "robot_dead.wav",
    "knight_dead": "knight_dead.wav",
    "dino_dead": "dino_dead.wav",
    "pumpkin_dead": "pumpkin_dead.wav",
    "grunt": "grunt.wav",
    "game_over": "game_over.wav",
    "ugh": "ugh.wav",
    "laugh": "laugh.ogg",
    "teleport": "teleport.wav",
}


class Music:
    """One looping track at a time (keys from config.MUSIC), fading between tracks."""

    def __init__(self, assets):
        self.assets = assets
        self.current = None      # the track asked for (tracked even without audio, for tests)
        self._fade_out = 0.0
        self.paused = False

    def play(self, key):
        if key == self.current:
            return
        self.current = key
        if not self.assets.audio:
            return
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(int(config.MUSIC_FADE * 1000))   # non-blocking in pygame 2
            self._fade_out = config.MUSIC_FADE
        else:
            self._start()

    def update(self, dt):
        if self._fade_out > 0 and not self.paused:
            self._fade_out -= dt
            if self._fade_out <= 0:
                self._start()

    def _start(self):
        name, volume = config.MUSIC[self.current]
        try:
            pygame.mixer.music.load(self.assets.path(name))
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(-1, fade_ms=500)
        except pygame.error:
            pass   # a missing track shouldn't stop the game

    def stop(self):
        self.current = None
        self._fade_out = 0.0
        self.paused = False
        if self.assets.audio:
            pygame.mixer.music.stop()

    def pause(self):
        self.paused = True
        if self.assets.audio:
            pygame.mixer.music.pause()

    def resume(self):
        self.paused = False
        if self.assets.audio:
            pygame.mixer.music.unpause()


class Sfx:
    """Name -> sound lookup so game code says sfx.play('punch')."""

    def __init__(self, assets):
        self.assets = assets

    def play(self, key):
        self.assets.play(SOUND_FILES[key])
