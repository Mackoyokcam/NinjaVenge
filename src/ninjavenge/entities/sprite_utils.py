"""Helpers for drawing directional sprites anchored at a body position."""
import pygame

_tint_cache = {}


def anchored_rect(image, x, floor_y, facing, anchor):
    """Place an image so its 'back' edge sits `anchor` px behind the body centre.

    Sprites face right; when facing left the image is mirrored, so the anchor
    flips to the other side. This keeps swords/corpses extending forward.
    """
    r = image.get_rect()
    if facing > 0:
        r.bottomleft = (round(x - anchor), round(floor_y))
    else:
        r.bottomright = (round(x + anchor), round(floor_y))
    return r


def tinted(image, color, mode):
    """Cached colour-tinted copy (mode: 'add' for flashes, 'mult' for hurt red)."""
    key = (id(image), color, mode)
    surf = _tint_cache.get(key)
    if surf is None:
        surf = image.copy()
        flag = pygame.BLEND_RGB_ADD if mode == "add" else pygame.BLEND_RGB_MULT
        surf.fill(color, special_flags=flag)
        if len(_tint_cache) > 512:
            _tint_cache.clear()
        _tint_cache[key] = surf
    return surf


def with_alpha(image, alpha):
    surf = image.copy()
    surf.fill((255, 255, 255, max(0, min(255, int(alpha)))), special_flags=pygame.BLEND_RGBA_MULT)
    return surf
