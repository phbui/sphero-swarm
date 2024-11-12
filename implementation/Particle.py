class Particle:
    def __init__(self, x, y, weight=1.0, color=None):
        self.x = x
        self.y = y
        self.prev_x = x  # Initialize previous position as the starting position
        self.prev_y = y
        self.weight = weight
        self.color = color  # Assign color to each particle

    def move(self, dx, dy, map_obj):
        # Update previous position before moving
        self.prev_x = self.x
        self.prev_y = self.y

        # Move with noise
        self.x += dx
        self.y += dy
