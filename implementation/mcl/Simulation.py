import cv2

class Simulation:
    def __init__(self, drones):
        self.drones = drones
        self.map = drones[0].map  # Assuming all drones share the same map
        
        # Verify if the map image loaded correctly
        if self.map.image is None:
            raise FileNotFoundError("Map image could not be loaded. Please check the path and file format.")
        self.original_map = self.map.image.copy()
        self.base_image = self.original_map.copy()  # Start with a clean copy
        self.draw_drones_on_base_image()

    def draw_drones_on_base_image(self):
        self.base_image = self.original_map.copy()

        for i, drone in enumerate(self.drones):
            # Convert drone's position to pixel coordinates
            pixel_x, pixel_y = self.map.map_to_pixel(drone.x, drone.y)
            # Draw the drone's position on the base image
            cv2.circle(self.base_image, (pixel_x, pixel_y), 14, (0, 0, 0), -1)  # Black border
            cv2.circle(self.base_image, (pixel_x, pixel_y), 10, drone.color, -1)

    def render_frame(self):
        # Start with the base image (drones drawn, no particles)
        frame = self.base_image.copy()
        
        # Draw particles on top for display
        for drone in self.drones:
            for particle in drone.mcl.particles:
                pixel_x, pixel_y = self.map.map_to_pixel(particle.x, particle.y)
                cv2.circle(frame, (pixel_x, pixel_y), 2, drone.color, -1)
        
        # Show the frame with particles overlaid on base image
        cv2.imshow("Monte Carlo Localization", frame)


    def move_drones(self, dx, dy, step_count):
        """Move all drones by the specified dx and dy."""
        for i, drone in enumerate(self.drones):
            # Move each drone and get the actual noisy movement
            actual_x, actual_y = drone.move(dx, dy, step_count)
            print(f"Drone {i+1} Actual Position: ({actual_x:.2f}, {actual_y:.2f})")

            # Update the base image with the new position of each drone
            self.draw_drones_on_base_image()

            # Update MCL particles with the new frame
            drone.mcl.map.image = self.base_image  # Update MCL with the new base image

            # Estimate position based on particles
            estimated_x, estimated_y = drone.mcl.estimate_position()
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
            # Check if the window is still open; break if it has been closed
            if cv2.getWindowProperty("Monte Carlo Localization", cv2.WND_PROP_VISIBLE) < 1:
                break

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
            self.move_drones(dx, dy, step_count)

            step_count += 1
                  
            # Render the updated frame after each movement
            self.render_frame()

        # Clean up and close the window
        cv2.destroyAllWindows()
