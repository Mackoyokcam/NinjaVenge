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

    def play_music(self, name="ninja.mp3", loops=-1):
        if not self.audio:
            return
        pygame.mixer.music.load(self.path(name))
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(loops)

    def stop_music(self):
        if self.audio:
            pygame.mixer.music.stop()

    def pause_music(self):
        if self.audio:
            pygame.mixer.music.pause()

    def resume_music(self):
        if self.audio:
            pygame.mixer.music.unpause()


SOUND_FILES = {
    "punch": "punch.wav",
    "attack": "attack.wav",
    "throw": "throw.wav",
    "jump": "jump.wav",
    "dink": "dink.wav",
    "robot_dead": "robot_dead.wav",
    "grunt": "grunt.wav",
    "game_over": "game_over.wav",
    "ugh": "ugh.wav",
    "laugh": "laugh.ogg",
}


class Sfx:
    """Name -> sound lookup so game code says sfx.play('punch')."""

    def __init__(self, assets):
        self.assets = assets

    def play(self, key):
        self.assets.play(SOUND_FILES[key])
