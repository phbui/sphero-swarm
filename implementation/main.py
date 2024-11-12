from Simulation import Simulation

if __name__ == "__main__":
    # Create and run the simulation
    simulation = Simulation(num_particles=1000, noise_sigma=0.1)
    simulation.run()
