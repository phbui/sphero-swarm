from Map import Map
from Drone import Drone
from Simulation import Simulation

if __name__ == "__main__":
    
    # Initialize the map
    map_obj = Map()
    map_obj.select_map()
    
    # Set parameters
    num_drones = 3
    noise_sigma = 0.1
    num_particles = 500
    
    # Create unique colors for each drone
    colors = [
        (0, 0, 255),    # Bright Red
        (255, 255, 0),  # Bright Cyan
        (20, 255, 57)   # Neon Green
    ]
    
    # Create drones with predefined colors and initialize MCL for each
    drones = [
        Drone(map_obj, noise_sigma, color=colors[i], num_particles=num_particles)
        for i in range(num_drones)
    ]
    
    # Create and run the simulation
    simulation = Simulation(drones=drones)
    simulation.run()
