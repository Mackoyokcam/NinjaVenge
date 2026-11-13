"""Time-based sprite animation."""


class Animation:
    def __init__(self, frames, duration, loop=True):
        """frames: (right_frames, left_frames). duration: seconds for one full cycle."""
        self.right, self.left = frames
        self.count = len(self.right)
        self.duration = duration
        self.loop = loop
        self.time = 0.0

    def reset(self):
        self.time = 0.0

    def update(self, dt):
        self.time += dt
        if self.loop:
            self.time %= self.duration

    @property
    def progress(self):
        """0..1 through the cycle (clamped at 1 for one-shot animations)."""
        return min(self.time / self.duration, 1.0)

    @property
    def done(self):
        return not self.loop and self.time >= self.duration

    @property
    def index(self):
        return min(int(self.progress * self.count), self.count - 1)

    def frame(self, facing):
        """facing: +1 right, -1 left."""
        return (self.right if facing > 0 else self.left)[self.index]
