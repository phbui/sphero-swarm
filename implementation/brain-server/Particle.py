import uuid

class Particle:
    def __init__(self, display, color):
        """
        Initialize a Particle instance.
        Args:
            display: Display instance for visualization.
            color: Color of the particle in hex format.
        """
        self.id = str(uuid.uuid4())  # Unique identifier for the particle
        self.display = display  # Reference to the display instance
        self.color = color  # Color of the particle
        self.x = 0  # X-coordinate of the particle
        self.y = 0  # Y-coordinate of the particle
        self.weight = 1  # Weight of the particle (used for resampling)

    def draw_particle(self):
        """
        Draw the particle on the display.
        """
        self.display.draw_point(self.id, self.x, self.y, self.weight, self.color)

    def move(self, x, y, weight):
        """
        Move the particle to a new position and update its weight.
        Args:
            x: New X-coordinate of the particle.
            y: New Y-coordinate of the particle.
            weight: New weight of the particle.
        """
        self.x = x  # Update X-coordinate
        self.y = y  # Update Y-coordinate
        self.weight = weight  # Update weight
        self.draw_particle()  # Redraw the particle at its new position
