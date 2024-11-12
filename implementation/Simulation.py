from Map import Map
from Drone import Drone
from MonteCarloLocalization import MonteCarloLocalization
import cv2

class Simulation:
    def __init__(self, num_particles=1000, noise_sigma=0.1):
        self.num_particles = num_particles
        self.noise_sigma = noise_sigma
        self.map = Map()
        self.map.select_map()
        
        # Verify if the map image loaded correctly
        if self.map.image is None:
            raise FileNotFoundError("Map image could not be loaded. Please check the path and file format.")
        
        self.drone = Drone(self.map, noise_sigma)
        self.mcl = MonteCarloLocalization(self.map, noise_sigma, num_particles)

    def render_frame(self):
        # Create a copy of the map for displaying particles and drone position
        map_copy = self.map.image.copy()
        
        # Draw particles
        for particle in self.mcl.particles:
            pixel_x, pixel_y = self.map.map_to_pixel(particle.x, particle.y)
            cv2.circle(map_copy, (pixel_x, pixel_y), 2, (255, 0, 0), -1)

        # Draw drone position
        pixel_x, pixel_y = self.map.map_to_pixel(self.drone.x, self.drone.y)
        cv2.circle(map_copy, (pixel_x, pixel_y), 10, (0, 0, 255), -1)

        # Display the map
        cv2.imshow("Monte Carlo Localization", map_copy)

    def run(self):
        print("Control the drone using W (up), A (left), S (down), D (right), and SPACE for no movement. Press Q to quit.")
        
        # Initialize the display window outside the loop
        cv2.namedWindow("Monte Carlo Localization", cv2.WINDOW_NORMAL)
        
        # Render the initial frame with the initial position
        print(f"Initial Drone Position: ({self.drone.x:.2f}, {self.drone.y:.2f})")
        self.render_frame()

        step_count = 0
        
        while True:
            # Wait for user input with a blocking call
            key = cv2.waitKey(0) & 0xFF  

            if key == ord('q'):
                break  # Exit the loop if 'q' is pressed
            elif key == ord('w'):
                dx, dy = 0, 1  # Move up
            elif key == ord('a'):
                dx, dy = -1, 0  # Move left
            elif key == ord('s'):
                dx, dy = 0, -1  # Move down
            elif key == ord('d'):
                dx, dy = 1, 0  # Move right
            elif key == ord(' '):  # SPACE for no movement
                dx, dy = 0, 0
            else:
                continue  # Ignore other keys

            # Display current position before moving
            print(f"Actual Drone Position: ({self.drone.x:.2f}, {self.drone.y:.2f})")

            # Move the drone and get the actual noisy movement
            actual_dx, actual_dy = self.drone.move(dx, dy)

            # Update particles based on the intended movement
            self.mcl.update_particles(dx, dy)

            # Estimate position based on particles
            estimated_x, estimated_y = self.mcl.estimate_position()
            print(f"Estimated Position: ({estimated_x:.2f}, {estimated_y:.2f})")

            # Resample particles every 5 steps
            if step_count % 5 == 0:
                self.mcl.resample_particles()
            step_count += 1

            # Render the updated frame after each movement
            self.render_frame()

        cv2.destroyAllWindows()
