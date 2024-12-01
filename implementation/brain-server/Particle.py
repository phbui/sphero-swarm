import uuid

class Particle:
    def __init__(self, display, color):
        self.id = str(uuid.uuid4())
        self.display = display
        self.color = color
        self.x = 0
        self.y = 0
        self.weight = 1

    def draw_particle(self):
        self.display.draw(self.id, self.x, self.y, self.weight, self.color)

    def move(self, x, y, weight):
        self.x = x
        self.y = y
        self.weight = weight
        self.draw_particle()

