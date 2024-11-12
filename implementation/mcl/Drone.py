import cv2
import random
import numpy as np
from MonteCarloLocalization import MonteCarloLocalization

def detect_drone_position_by_color(image, color, tolerance=30):
    """Detect the approximate position of a drone by its color in the image."""
    # Define the color range
    lower_bound = np.array([max(c - tolerance, 0) for c in color], dtype=np.uint8)
    upper_bound = np.array([min(c + tolerance, 255) for c in color], dtype=np.uint8)
    
    # Mask the image to only include the color range
    mask = cv2.inRange(image, lower_bound, upper_bound)
    
    # Find the contours of the masked area
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        # Use the largest contour to find the center of the detected area
        largest_contour = max(contours, key=cv2.contourArea)
        M = cv2.moments(largest_contour)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            return cx, cy  # Return the detected center
    return None  # Return None if the color is not found

class Drone:
    def __init__(self, map_obj, noise_sigma, color, num_particles=1000, initial_image=None):
        self.map = map_obj
        self.noise_sigma = noise_sigma
        self.color = color  # Each drone has its own color
        
        # Detect the drone's initial position by color
        if initial_image is not None:
            position = detect_drone_position_by_color(initial_image, color)
            if position:
                self.x, self.y = position  # Set initial position to detected position
            else:
                # Default to random if detection fails
                self.x = random.uniform(self.map.x_min, self.map.x_max)
                self.y = random.uniform(self.map.y_min, self.map.y_max)
        else:
            self.x = random.uniform(self.map.x_min, self.map.y_max)
            self.y = random.uniform(self.map.y_min, self.map.y_max)

        # Initialize MCL with detected position
        self.mcl = MonteCarloLocalization(self.map, noise_sigma, num_particles, color=self.color, initial_x=self.x, initial_y=self.y)
        print(f"Initial Drone Position: ({self.x}, {self.y}), Color: {self.color}")

    def move(self, dx, dy):
        # Apply movement noise and update position
        actual_dx = dx + random.gauss(0, self.noise_sigma * 0.1)
        actual_dy = dy + random.gauss(0, self.noise_sigma * 0.1)

        self.x += actual_dx
        self.y += actual_dy

        # Update MCL particles
        self.mcl.update_particles(dx, dy)

        return self.x, self.y
