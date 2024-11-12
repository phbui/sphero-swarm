import cv2

class Simulation:
    def __init__(self, drones, particles):
        self.drones = drones
        self.mcls = particles
        self.map = drones[0].map  # Assuming all drones share the same map
        
        # Verify if the map image loaded correctly
        if self.map.image is None:
            raise FileNotFoundError("Map image could not be loaded. Please check the path and file format.")

    def render_frame(self):
        # Create a copy of the map for displaying particles and drone positions
        map_copy = self.map.image.copy()
        
        # Draw each drone's particles and position
        for i, (mcl, drone) in enumerate(zip(self.mcls, self.drones)):
            # Draw particles for this drone in its color
            for particle in mcl.particles:
                pixel_x, pixel_y = self.map.map_to_pixel(particle.x, particle.y)
                cv2.circle(map_copy, (pixel_x, pixel_y), 2, drone.color, -1)

            # Draw the drone's position in its color
            pixel_x, pixel_y = self.map.map_to_pixel(drone.x, drone.y)
            cv2.circle(map_copy, (pixel_x, pixel_y), 10, drone.color, -1)
            cv2.putText(map_copy, f"Drone {i+1}", (pixel_x - 20, pixel_y - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, drone.color, 1)

        # Display the map
        cv2.imshow("Monte Carlo Localization", map_copy)

    def move_drones(self, dx, dy):
        """Move all drones by the specified dx and dy."""
        for i, (drone, mcl) in enumerate(zip(self.drones, self.mcls)):
            # Move each drone and get the actual noisy movement
            actual_dx, actual_dy = drone.move(dx, dy)

            # Update particles based on the intended movement
            mcl.update_particles(dx, dy)

            # Estimate position based on particles
            estimated_x, estimated_y = mcl.estimate_position()
            print(f"Drone {i+1} Estimated Position: ({estimated_x:.2f}, {estimated_y:.2f})")

    def run(self):
        print("Control the drones using W (up), A (left), S (down), D (right), and SPACE for no movement. Press Q to quit.")
        
        # Initialize the display window with the original image size
        cv2.namedWindow("Monte Carlo Localization", cv2.WINDOW_NORMAL)
        
        # Render the initial frame with the initial positions
        for i, drone in enumerate(self.drones):
            print(f"Initial Drone {i+1} Position: ({drone.x:.2f}, {drone.y:.2f}), Color: {drone.color}")
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

            # Move all drones based on input
            self.move_drones(dx, dy)

            # Resample particles every 5 steps for each drone
            if step_count % 5 == 0:
                for mcl in self.mcls:
                    mcl.resample_particles()

            step_count += 1

            # Render the updated frame after each movement
            self.render_frame()

        cv2.destroyAllWindows()
