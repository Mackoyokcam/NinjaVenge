"""One game loop that drives a stack of scenes."""
import pygame

from . import config as C
from .assets import Assets
from .profile import Profile


class Scene:
    """Base class. The top scene on the stack gets events and updates."""

    def __init__(self, app):
        self.app = app

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass

    def on_quit(self):
        """Called when the app closes while this scene is on the stack."""


class App:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        if not pygame.font:
            print("Warning, fonts disabled")
        self.screen = pygame.display.set_mode((C.SCREEN_W, C.SCREEN_H))
        pygame.display.set_caption(C.TITLE)
        self.clock = pygame.time.Clock()
        self.assets = Assets()
        self.profile = Profile()
        self._fonts = {}
        self.stack = []
        self.running = True

    def font(self, size):
        if size not in self._fonts:
            self._fonts[size] = pygame.font.Font(None, size)
        return self._fonts[size]

    # scene management
    def change(self, scene):
        self.stack = [scene]

    def push(self, scene):
        self.stack.append(scene)

    def pop(self):
        self.stack.pop()

    def quit(self):
        if self.running:
            for scene in self.stack:
                scene.on_quit()
        self.running = False

    @property
    def scene(self):
        return self.stack[-1]

    def step(self, dt, events):
        """Advance one frame. Split out from run() so tests can drive it headlessly."""
        for event in events:
            if event.type == pygame.QUIT:
                self.quit()
                return
            self.scene.handle_event(event)
            if not self.running:
                return
        self.scene.update(dt)
        if self.running:
            self.scene.draw(self.screen)

    def run(self, first_scene):
        self.change(first_scene)
        while self.running:
            dt = min(self.clock.tick(C.FPS) / 1000.0, C.MAX_DT)
            self.step(dt, pygame.event.get())
            pygame.display.flip()
        pygame.quit()
