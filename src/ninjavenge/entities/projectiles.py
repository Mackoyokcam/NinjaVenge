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
