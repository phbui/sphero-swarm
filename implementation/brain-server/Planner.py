import threading
import Camera
import Display
import Drone
import Map


class Planner:
    def __init__(self, spheros):
        self.display = Display.Display()
        self.camera = Camera.Camera(self.display)
        self.camera.capture_image()
        self.display_thread = threading.Thread(target=self.display.show, daemon=True)
        self.display_thread.start()
        self.map = Map.Map(self.display)
        self.map.generate_prm()
        self.spheros = [Drone.Drone(self.display, sphero["id"], sphero["color"],  self.map) for sphero in spheros]

    def start(self, ws):
        """Iterate over all Spheros and trigger their next moves."""
        print("System started.")
        for sphero in self.spheros:
            sphero.execute_state(ws)

    def next_move(self, ws, id):
        """Trigger the next move for a specific Sphero."""
        for sphero in self.spheros:
            if sphero.sphero_id == id:
                sphero.execute_state(ws)

