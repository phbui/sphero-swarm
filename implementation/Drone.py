import random

class Drone:
    def __init__(self, map_obj, noise_sigma):
        self.map = map_obj
        self.x = random.uniform(self.map.x_min, self.map.x_max)
        self.y = random.uniform(self.map.y_min, self.map.y_max)
        self.noise_sigma = noise_sigma
        print(f"Initial Drone Position: ({self.x}, {self.y})")

    def move(self, dx, dy):
        # Apply movement noise
        actual_dx = dx + random.gauss(0, self.noise_sigma)
        actual_dy = dy + random.gauss(0, self.noise_sigma)

        # Update position with noise
        self.x += actual_dx
        self.y += actual_dy

        # Ensure the drone stays within the map bounds
        self.x = max(min(self.x, self.map.x_max), self.map.x_min)
        self.y = max(min(self.y, self.map.y_max), self.map.y_min)

        return actual_dx, actual_dy  # Return the actual noisy movement
