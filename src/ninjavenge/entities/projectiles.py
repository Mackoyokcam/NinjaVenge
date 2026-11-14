import pygame

from .. import config as C


class Kunai:
    def __init__(self, assets, x, y, facing, speed=C.KUNAI_SPEED):
        right = assets.image("Kunai.png")
        self.image = right if facing > 0 else pygame.transform.flip(right, True, False)
        self.x, self.y = float(x), float(y)
        self.facing = facing
        self.speed = speed
        self.alive = True

    @property
    def rect(self):
        r = pygame.Rect(0, 0, 50, 14)
        r.center = (round(self.x + self.facing * 15), round(self.y))
        return r

    def update(self, dt):
        self.x += self.facing * self.speed * dt
        if self.x < -100 or self.x > C.SCREEN_W + 100:
            self.alive = False

    def draw(self, surf):
        r = self.image.get_rect(center=(round(self.x), round(self.y)))
        surf.blit(self.image, r)


class Bullet:
    def __init__(self, x, y, facing):
        self.x, self.y = float(x), float(y)
        self.facing = facing
        self.speed = C.BULLET_SPEED
        self.friendly = False   # True once deflected: it hurts enemies instead of Ren
        self.alive = True

    def reflect(self):
        """Send the bullet back the way it came."""
        self.facing = -self.facing
        self.speed *= C.RICOCHET_SPEED_MULT
        self.friendly = True

    @property
    def rect(self):
        r = pygame.Rect(0, 0, 16, 8)
        r.center = (round(self.x), round(self.y))
        return r

    def update(self, dt):
        self.x += self.facing * self.speed * dt
        if self.x < -50 or self.x > C.SCREEN_W + 50:
            self.alive = False

    def draw(self, surf):
        tail = (round(self.x - self.facing * 26), round(self.y))
        trail, core = ((80, 200, 255), (220, 250, 255)) if self.friendly else ((255, 170, 60), (255, 240, 170))
        pygame.draw.line(surf, trail, tail, (round(self.x), round(self.y)), 3)
        pygame.draw.circle(surf, core, (round(self.x), round(self.y)), 4)


class Shuriken(Bullet):
    """Kage's throwing star. Behaves like a bullet: hurts Ren, a sword slash sends it back."""

    def __init__(self, x, y, facing):
        super().__init__(x, y, facing)
        self.speed = C.SHURIKEN_SPEED
        self.spin = 0.0

    @property
    def rect(self):
        r = pygame.Rect(0, 0, 24, 24)
        r.center = (round(self.x), round(self.y))
        return r

    def update(self, dt):
        super().update(dt)
        self.spin += dt * 22 * self.facing

    def draw(self, surf):
        import math
        steel, edge = ((150, 220, 255), (230, 250, 255)) if self.friendly else ((185, 190, 205), (245, 245, 250))
        pts = []
        for i in range(8):
            a = self.spin + i * math.pi / 4
            r = 14 if i % 2 == 0 else 5
            pts.append((self.x + math.cos(a) * r, self.y + math.sin(a) * r))
        pygame.draw.polygon(surf, steel, pts)
        pygame.draw.polygon(surf, (40, 40, 50), pts, 1)
        pygame.draw.circle(surf, edge, (round(self.x), round(self.y)), 3)
