class Particle:
    def __init__(self, x, y, weight=1.0):
        self.x = x
        self.y = y
        self.prev_x = x  # Initialize previous position as the starting position
        self.prev_y = y
        self.weight = weight

    def move(self, dx, dy):
        # Update previous position before moving
        self.prev_x = self.x
        self.prev_y = self.y

        # Move with noise
        self.x += dx
        self.y += dy
