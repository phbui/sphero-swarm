import Localizer

class Drone:
    def __init__(self, display, sphero_id, sphero_color):
        self.display = display
        self.sphero_id = sphero_id
        self.sphero_color= sphero_color
        print(f"Sphero Initialized: {sphero_id}")
        self.localizer = Localizer.Localizer(display, sphero_color, 100)
        self.x, self.y = self.get_position()
        print(f"Sphero [{self.sphero_id}]: Initial x: {self.x}, Initial y: {self.y}")

    def get_position(self):
        return self.localizer.updateParticles()

    def move(self):
        print(f"Sphero [{self.sphero_id}]: Current x: {self.x}, Current y: {self.y}")
        return self.x, self.y
