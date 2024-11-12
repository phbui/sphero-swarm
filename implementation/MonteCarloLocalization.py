import random
import numpy as np
from Particle import Particle
from copy import deepcopy

class MonteCarloLocalization:
    def __init__(self, map_obj, noise_sigma, num_particles=1000):
        self.map = map_obj
        self.noise_sigma = noise_sigma
        self.num_particles = num_particles
        self.particles = self.initialize_particles()

    def initialize_particles(self):
        particles = []
        for _ in range(self.num_particles):
            x = random.uniform(self.map.x_min, self.map.x_max)
            y = random.uniform(self.map.y_min, self.map.y_max)
            particles.append(Particle(x, y, self.noise_sigma))
        return particles

    def update_particles(self, dx, dy):
        # Update particle positions based on the intended drone movement with noise
        for particle in self.particles:
            particle.move(dx, dy, self.map)

        # Update particle weights based on how closely they match the intended movement
        self.update_weights(dx, dy)

    def update_weights(self, dx, dy):
        # Calculate intended movement angle
        intended_angle = np.arctan2(dy, dx)
        
        for particle in self.particles:
            # Calculate particle's movement angle
            particle_dx = particle.x - particle.prev_x
            particle_dy = particle.y - particle.prev_y
            particle_angle = np.arctan2(particle_dy, particle_dx)
            
            # Calculate angular difference from intended direction
            angle_diff = abs(intended_angle - particle_angle)
            angle_diff = min(angle_diff, 2 * np.pi - angle_diff)  # Normalize to [0, pi]
            
            # Update weight inversely proportional to angle difference, with Gaussian weighting
            particle.weight = np.exp(-angle_diff**2 / (2 * self.noise_sigma**2))
            
        # Normalize weights
        total_weight = sum(p.weight for p in self.particles)
        if total_weight > 0:
            for particle in self.particles:
                particle.weight /= total_weight
        else:
            # If all weights are zero, assign equal weight to all particles to prevent division by zero
            for particle in self.particles:
                particle.weight = 1.0 / self.num_particles

    def estimate_position(self):
        # Weighted mean estimation for x and y coordinates
        x_estimate = sum(p.x * p.weight for p in self.particles)
        y_estimate = sum(p.y * p.weight for p in self.particles)
        return x_estimate, y_estimate

    def resample_particles(self):
        # Resample particles using weights to maintain concentration around high-weight areas
        weights = [p.weight for p in self.particles]
        if np.sum(weights) == 0:
            return  # Avoid division by zero

        weights /= np.sum(weights)
        indices = np.random.choice(range(self.num_particles), size=self.num_particles, p=weights)
        new_particles = [deepcopy(self.particles[i]) for i in indices]

        # Add some noise inversely proportional to weight for better localization
        for particle in new_particles:
            std_dev = (1 - particle.weight) * self.noise_sigma * 0.5
            particle.x += random.gauss(0, std_dev)
            particle.y += random.gauss(0, std_dev)

            # Ensure particles stay within map boundaries
            particle.x = max(min(particle.x, self.map.x_max), self.map.x_min)
            particle.y = max(min(particle.y, self.map.y_max), self.map.y_min)

        self.particles = new_particles
