import random
import numpy as np
from Particle import Particle
from copy import deepcopy
import cv2

class MonteCarloLocalization:
    def __init__(self, map_obj, noise_sigma, num_particles=1000, color=None, initial_x=None, initial_y=None):
        # MCL setup with map reference, noise parameter, particle count, and drone color
        self.map = map_obj
        self.noise_sigma = noise_sigma
        self.num_particles = num_particles
        self.color = color 
        self.particles = self.initialize_particles(initial_x, initial_y) 

    def initialize_particles(self, initial_x=None, initial_y=None, spread=1.0):
        # Initializes particles, centered around initial coordinates if given, or random across the map
        particles = []
        for _ in range(self.num_particles):
            if initial_x is not None and initial_y is not None:
                x = random.uniform(initial_x - spread, initial_x + spread)
                y = random.uniform(initial_y - spread, initial_y + spread)
            else:
                x = random.uniform(self.map.x_min, self.map.x_max)
                y = random.uniform(self.map.y_min, self.map.y_max)
            particles.append(Particle(x, y))
        return particles

    def update_particles(self, dx, dy, detected_position=None):
        # Shifts particles based on intended movement, updating each particle's position and weight
        for particle in self.particles:
            noise_x = np.random.normal(0, self.noise_sigma)
            noise_y = np.random.normal(0, self.noise_sigma)
            particle.move(dx + noise_x, dy + noise_y) 
        self.update_weights(dx, dy, detected_position)

    def get_map_color_at_particle(self, particle):
        # Finds the map color where each particle is located for color-based localization
        # Convert particle's map coordinates to pixel coordinates
        pixel_x, pixel_y = self.map.map_to_pixel(particle.x, particle.y)
        # Ensure pixel coordinates are within image bounds
        height, width, _ = self.map.image.shape
        pixel_x = int(np.clip(pixel_x, 0, width - 1))
        pixel_y = int(np.clip(pixel_y, 0, height - 1))
        # Retrieve the color at the pixel location (in BGR format)
        map_color_bgr = self.map.image[pixel_y, pixel_x]
        # Convert BGR to RGB
        map_color_rgb = map_color_bgr[::-1]
        return tuple(map_color_rgb)


    def color_similarity_weight(self, map_color):
        # Convert colors to HSV for better comparison
        drone_color_hsv = cv2.cvtColor(np.uint8([[self.color]]), cv2.COLOR_RGB2HSV)[0][0]
        map_color_hsv = cv2.cvtColor(np.uint8([[map_color]]), cv2.COLOR_RGB2HSV)[0][0]
        # Compute color difference
        color_diff = np.linalg.norm(drone_color_hsv - map_color_hsv)
        # Compute weight (smaller difference -> higher weight)
        sigma_color = 20 
        return np.exp(-color_diff**2 / (2 * sigma_color**2))

    def update_weights(self, dx, dy, detected_position=None):
        # Updates particle weights based on both motion and color
        intended_angle = np.arctan2(dy, dx)

        for particle in self.particles:
            # Calculate particle's movement angle
            particle_dx = particle.x - particle.prev_x
            particle_dy = particle.y - particle.prev_y
            particle_angle = np.arctan2(particle_dy, particle_dx)
            
            # Calculate angular difference from intended direction
            angle_diff = abs(intended_angle - particle_angle)
            angle_diff = min(angle_diff, 2 * np.pi - angle_diff)
            
            # Get map color at particle's position
            map_color = self.get_map_color_at_particle(particle)
            
            # Color similarity-based weight
            color_weight = self.color_similarity_weight(map_color)
            
            # Combined weight (motion + color)
            motion_weight = np.exp(-angle_diff**2 / (2 * 0.1**2)) 
            particle.weight = motion_weight * (color_weight ** 2)
            
            # If detected position is available, add a correction factor based on distance to detected color position
            if detected_position:
                detected_x, detected_y = self.map.pixel_to_map(detected_position[0], detected_position[1])
                distance_to_detected = np.hypot(particle.x - detected_x, particle.y - detected_y)
                correction_weight = np.exp(-distance_to_detected**2 / (2 * self.noise_sigma**2))
                particle.weight *= correction_weight

        # Normalize weights
        total_weight = sum(p.weight for p in self.particles)
        if total_weight > 0:
            for particle in self.particles:
                particle.weight /= total_weight
        else:
            for particle in self.particles:
                particle.weight = 1.0 / self.num_particles

    def estimate_position(self):
        # Estimates the drone's position based on weighted mean of particle positions
        x_estimate = sum(p.x * p.weight for p in self.particles)
        y_estimate = sum(p.y * p.weight for p in self.particles)
        return x_estimate, y_estimate

    def resample_particles(self, detected_position=None):
        # Resamples particles based on their weights
        weights = [p.weight for p in self.particles]
        if np.sum(weights) == 0:
            return

        weights /= np.sum(weights)
        indices = np.random.choice(range(self.num_particles), size=self.num_particles, p=weights)
        new_particles = [deepcopy(self.particles[i]) for i in indices]

        # Use adaptive correction based on particle spread
        x_spread = np.std([p.x for p in self.particles])
        y_spread = np.std([p.y for p in self.particles])
        adaptive_noise = min(self.noise_sigma * 0.1, x_spread, y_spread)

        # Detect the current drone position by color
        if detected_position:
            detected_x, detected_y = self.map.pixel_to_map(detected_position[0], detected_position[1])
        
        # Adjust particle positions to concentrate around the detected position
        for particle in new_particles:
            if detected_position:
                particle.x = detected_x + random.gauss(0, adaptive_noise)
                particle.y = detected_y + random.gauss(0, adaptive_noise)
            else:
                particle.x += random.gauss(0, adaptive_noise)
                particle.y += random.gauss(0, adaptive_noise)

        self.particles = new_particles
