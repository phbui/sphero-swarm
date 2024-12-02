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

        self.spheros = [Drone.Drone(self.display, sphero["id"], sphero["color"]) for sphero in spheros]
        self.map = Map.Map(self.display, self.spheros)
        self.goal = self.map.get_goal_location()

        # Assign the global goal to each Sphero
        for sphero in self.spheros:
            sphero.goal = self.goal
            sphero.prm_nodes = self.map.roadmap["nodes"]  # Initial PRM nodes

    def resample_prm(self):
        """Resample the PRM and update nodes for all Spheros."""
        self.map.generate_prm()  # Resample the PRM
        new_nodes = self.map.roadmap["nodes"]

        for sphero in self.spheros:
            sphero.prm_nodes = new_nodes  # Update the PRM nodes in each Drone

    async def next_move(self, ws, id):
        """Trigger the next move for a specific Sphero."""
        for sphero in self.spheros:
            if sphero.sphero_id == id:
                await sphero.execute_state(ws)
                self.resample_prm()  # Resample PRM after the move
