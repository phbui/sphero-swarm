import random
import numpy as np
from Particle import Particle
from copy import deepcopy

class MonteCarloLocalization:
    def __init__(self, map_obj, noise_sigma, num_particles=1000, color=None, initial_x=None, initial_y=None):
        self.map = map_obj
        self.noise_sigma = noise_sigma
        self.num_particles = num_particles
        self.color = color 
        self.particles = self.initialize_particles(initial_x, initial_y) 

    def initialize_particles(self, initial_x=None, initial_y=None, spread=2.0):
        particles = []
        for _ in range(self.num_particles):
            if initial_x is not None and initial_y is not None:
                # Initialize particle within a small spread around initial_x, initial_y
                x = random.uniform(initial_x - spread, initial_x + spread)
                y = random.uniform(initial_y - spread, initial_y + spread)
                particle_color = tuple(min(max(c + random.randint(-30, 30), 0), 255) for c in self.color)
            else:
                # Uniform distribution across map if no initial position is given
                x = random.uniform(self.map.x_min, self.map.x_max)
                y = random.uniform(self.map.y_min, self.map.y_max)
                particle_color = self.color

            particles.append(Particle(x, y, color=particle_color))
        return particles

    def update_particles(self, dx, dy):
        for particle in self.particles:
            particle.move(dx, dy, self.map)  
        self.update_weights(dx, dy)

    def color_similarity_weight(self, particle_color):
        if self.color is None or particle_color is None:
            return 1.0
        color_diff = np.sqrt(sum((pc - dc) ** 2 for pc, dc in zip(particle_color, self.color)))
        return np.exp(-color_diff / (2 * 255 ** 2))

    def update_weights(self, dx, dy):
        intended_angle = np.arctan2(dy, dx)
        
        for particle in self.particles:
            particle_dx = particle.x - particle.prev_x
            particle_dy = particle.y - particle.prev_y
            particle_angle = np.arctan2(particle_dy, particle_dx)
            
            angle_diff = abs(intended_angle - particle_angle)
            angle_diff = min(angle_diff, 2 * np.pi - angle_diff)
            
            color_weight = self.color_similarity_weight(particle.color) ** 2  # Increase color weight impact
            motion_weight = np.exp(-angle_diff**2 / (2 * 0.05**2))  # Narrow Gaussian
            particle.weight = motion_weight * color_weight
        
        total_weight = sum(p.weight for p in self.particles)
        if total_weight > 0:
            for particle in self.particles:
                particle.weight /= total_weight
        else:
            for particle in self.particles:
                particle.weight = 1.0 / self.num_particles

    def estimate_position(self):
        x_estimate = sum(p.x * p.weight for p in self.particles)
        y_estimate = sum(p.y * p.weight for p in self.particles)
        return x_estimate, y_estimate

    def resample_particles(self):
        weights = [p.weight for p in self.particles]
        if np.sum(weights) == 0:
            return

        weights /= np.sum(weights)
        indices = np.random.choice(range(self.num_particles), size=self.num_particles, p=weights)
        new_particles = [deepcopy(self.particles[i]) for i in indices]

        # Reduce or eliminate noise added in resampling
        for particle in new_particles:
            adaptive_noise = self.noise_sigma * 0.01  # Small or zero noise
            particle.x += random.gauss(0, adaptive_noise)
            particle.y += random.gauss(0, adaptive_noise)

        self.particles = new_particles
