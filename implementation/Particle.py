import random

class Particle:
    def __init__(self, x, y, noise_sigma, weight=1.0):
        self.x = x
        self.y = y
        self.prev_x = x  # Initialize previous position as the starting position
        self.prev_y = y
        self.weight = weight
        self.noise_sigma = noise_sigma

    def move(self, dx, dy, map_obj):
        # Update previous position before moving
        self.prev_x = self.x
        self.prev_y = self.y

        # Move with noise
        self.x += dx + random.gauss(0, self.noise_sigma)
        self.y += dy + random.gauss(0, self.noise_sigma)

        # Keep particle within bounds
        self.x = max(min(self.x, map_obj.x_max), map_obj.x_min)
        self.y = max(min(self.y, map_obj.y_max), map_obj.y_min)
