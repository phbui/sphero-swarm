import threading
import Camera
import Display
import Drone
import Map

class Planner:
    def __init__(self, spheros):
        """
        Initialize the Planner class to manage the overall system.
        Args:
            spheros: List of dictionaries, where each dictionary contains the "id" and "color" of a Sphero.
        """
        self.display = Display.Display()  # Initialize the display instance
        self.camera = Camera.Camera(self.display)  # Initialize the camera instance with the display
        self.camera.capture_image()  # Capture an initial image from the camera

        # Start a separate thread for continuously showing the display
        self.display_thread = threading.Thread(target=self.display.show, daemon=True)
        self.display_thread.start()

        # Initialize the map and generate the probabilistic roadmap (PRM)
        self.map = Map.Map(self.display)
        self.map.generate_prm()

        # Initialize the list of Spheros (Drones)
        self.spheros = [
            Drone.Drone(self.camera, self.display, sphero["id"], sphero["color"], self.map)
            for sphero in spheros
        ]

    def start(self, ws):
        """
        Start the system by iterating over all Spheros and triggering their next moves.
        Args:
            ws: WebSocket connection to send updates.
        """
        print("System started.")
        for sphero in self.spheros:
            sphero.execute_state(ws)  # Trigger the state execution for each Sphero

    def next_move(self, ws, id):
        """
        Trigger the next move for a specific Sphero based on its ID.
        Args:
            ws: WebSocket connection to send updates.
            id: The unique ID of the Sphero to control.
        """
        for sphero in self.spheros:
            if sphero.sphero_id == id:  # Match the Sphero by ID
                sphero.execute_state(ws)  # Trigger its state execution
