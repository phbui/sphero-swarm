import threading
import Camera
import Display
import Drone
import Map

class Planner:
     def __init__(self, spheros):
          """
          Initialize the Planner class with the given spheros.
          Args:
               spheros (list): List of sphero dictionaries containing 'id' and 'color'.
          """
          self.display = Display.Display()  # Initialize Display
          self.camera = Camera.Camera(self.display)  # Pass Display to Camera

          # Capture an initial image to set dimensions
          self.camera.capture_image()

          # Start the display in a separate thread
          self.display_thread = threading.Thread(target=self.display.show, daemon=True)
          self.display_thread.start()

          # Initialize drones
          self.spheros = [
               Drone.Drone(self.display, sphero["id"], sphero["color"])
               for sphero in spheros
          ]

          self.map = Map.Map(self.display, self.spheros)

          self.debug_move()

          print(f"Planner initialized with Spheros: {spheros}\n")

     def stop(self):
          """
          Stop the display and release resources.
          """
          self.display.stop()  # Stop the display loop
          self.camera.release_camera()  # Release the camera resource

     def move(self, sphero_id, target_x, target_y):
               """
               Capture an image, find the corresponding sphero by ID, and move it.
               """
               # Capture an image with the camera
               self.camera.capture_image()
               
               # Find the Sphero with the matching ID
               target_sphero = None
               for sphero in self.spheros:
                    if sphero.sphero_id == sphero_id:
                         target_sphero = sphero
                         break
               
               # If the Sphero is found, call its move method
               if target_sphero:
                    print(f"Found Sphero: {sphero_id}")
                    initial_x, initial_y = target_sphero.move()

                    return initial_x, initial_y, target_x, target_y
               else:
                    print(f"Sphero with ID {sphero_id} not found.")

     def debug_move(self):
          """
          Randomly selects a Sphero by ID and moves it every second using the move method.
          """
          print("Starting debug move...")
          while True:

               # Call the move method for the selected Sphero
               self.move("Alpha")

