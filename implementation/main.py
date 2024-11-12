from Map import Map
from Drone import Drone
from Simulation import Simulation
from MonteCarloLocalization import MonteCarloLocalization

if __name__ == "__main__":
    import random
    
    # Initialize the map
    map_obj = Map()
    map_obj.select_map()
    
    # Set parameters
    num_drones = 3
    noise_sigma = 0.1
    num_particles = 3000
    
    # Create unique colors for each drone
    colors = [
        (255, 0, 0),    # Bright Red
        (0, 255, 255),  # Bright Cyan
        (57, 255, 20)   # Neon Green
    ]
    
    # Create drones with predefined colors and initialize MCL for each
    drones = [
        Drone(map_obj, noise_sigma, color=colors[i], num_particles=num_particles)
        for i in range(num_drones)
    ]
    
    # Initialize MCL for each drone with specified particle count
    particles = [MonteCarloLocalization(map_obj, noise_sigma, num_particles) for _ in range(num_drones)]
    
    # Create and run the simulation
    simulation = Simulation(drones=drones, particles=particles)
    simulation.run()
