import random
import numpy as np
from Particle import Particle
from copy import deepcopy

class MonteCarloLocalization:
    def __init__(self, map_obj, noise_sigma, num_particles=1000, color=None, initial_x=None, initial_y=None):
        self.map = map_obj
        self.noise_sigma = noise_sigma
        self.num_particles = num_particles
        self.color = color  # Reference color for particles
        self.particles = self.initialize_particles(initial_x, initial_y)  # Initialize particles near initial position

    def initialize_particles(self, initial_x=None, initial_y=None, spread=2.0):
        particles = []
        for _ in range(self.num_particles):
            if initial_x is not None and initial_y is not None:
                # Initialize particle within a small spread around initial_x, initial_y
                x = random.uniform(initial_x - spread, initial_x + spread)
                y = random.uniform(initial_y - spread, initial_y + spread)
                # Color similar to the drone's color
                particle_color = tuple(
                    min(max(c + random.randint(-30, 30), 0), 255) for c in self.color
                )
            else:
                # Uniform distribution across map if no initial position is given
                print("\nNo Position Given.")
                x = random.uniform(self.map.x_min, self.map.x_max)
                y = random.uniform(self.map.y_min, self.map.y_max)
                particle_color = self.color

            # Create particle with specified position, noise, and color
            particles.append(Particle(x, y, self.noise_sigma, color=particle_color))
        return particles
    
    def update_particles(self, dx, dy):
        # Update particle positions based on the intended drone movement with noise
        for particle in self.particles:
            particle.move(dx, dy, self.map)

        # Update particle weights based on how closely they match the intended movement
        self.update_weights(dx, dy)

    def color_similarity_weight(self, particle_color):
        """Calculate a weight based on the similarity between the drone color and a particle color."""
        if self.color is None or particle_color is None:
            return 1.0
        color_diff = np.sqrt(sum((pc - dc) ** 2 for pc, dc in zip(particle_color, self.color)))
        return np.exp(-color_diff / (2 * 255 ** 2))  # Gaussian decay based on color distance

    def update_weights(self, dx, dy):
        intended_angle = np.arctan2(dy, dx)
        
        for particle in self.particles:
            # Calculate particle's movement angle
            particle_dx = particle.x - particle.prev_x
            particle_dy = particle.y - particle.prev_y
            particle_angle = np.arctan2(particle_dy, particle_dx)
            
            # Calculate angular difference from intended direction
            angle_diff = abs(intended_angle - particle_angle)
            angle_diff = min(angle_diff, 2 * np.pi - angle_diff)
            
            # Color similarity-based weight
            color_weight = self.color_similarity_weight(particle.color)
            
            # Combined weight (motion + color)
            motion_weight = np.exp(-angle_diff**2 / (2 * self.noise_sigma**2))
            particle.weight = motion_weight * color_weight
        
        # Normalize weights
        total_weight = sum(p.weight for p in self.particles)
        if total_weight > 0:
            for particle in self.particles:
                particle.weight /= total_weight
        else:
            # Default equal weights if all weights are zero
            for particle in self.particles:
                particle.weight = 1.0 / self.num_particles

    def estimate_position(self):
        # Weighted mean estimation for x and y coordinates
        x_estimate = sum(p.x * p.weight for p in self.particles)
        y_estimate = sum(p.y * p.weight for p in self.particles)
        return x_estimate, y_estimate

    def resample_particles(self):
        weights = [p.weight for p in self.particles]
        if np.sum(weights) == 0:
            return  # Avoid division by zero

        weights /= np.sum(weights)
        indices = np.random.choice(range(self.num_particles), size=self.num_particles, p=weights)
        new_particles = [deepcopy(self.particles[i]) for i in indices]

        # Adaptive noise reduction
        for particle in new_particles:
            # Scale noise based on weight to refine position for high-weight particles
            adaptive_noise = self.noise_sigma * (1 - particle.weight)
            particle.x += random.gauss(0, adaptive_noise)
            particle.y += random.gauss(0, adaptive_noise)

            # Ensure particles stay within map boundaries
            particle.x = max(min(particle.x, self.map.x_max), self.map.x_min)
            particle.y = max(min(particle.y, self.map.y_max), self.map.y_min)

        self.particles = new_particles

