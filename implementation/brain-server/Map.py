import numpy as np
import random
from scipy.spatial import KDTree


class Map:
    def __init__(self, display, spheros):
        self.display = display
        self.spheros = spheros
        self.obstacle_localizer = Localizer(display, 'orange', 500)  # Detect obstacles
        self.goal_localizer = Localizer(display, 'purple', 500)  # Detect goal state
        self.roadmap = None

    def generate_prm(self, num_samples=100, k_neighbors=5):
        """
        Generate a probabilistic road map (PRM) using the Localizer.
        Args:
            num_samples (int): Number of samples in free space.
            k_neighbors (int): Number of nearest neighbors to connect.
        """
        print("Generating PRM...")
        
        # Get obstacle and goal regions
        obstacles = self.get_obstacle_regions()
        goal = self.get_goal_location()

        # Sample free space
        free_space_samples = self.sample_free_space(obstacles, num_samples)

        # Connect samples using k-nearest neighbors
        self.roadmap = self.connect_samples(free_space_samples, obstacles, k_neighbors)

        # Add the goal as a node
        self.roadmap["nodes"].append(goal)
        self.roadmap["edges"].append([])  # Empty connections for now
        
        print("PRM generation complete.")
        return self.roadmap

    def get_obstacle_regions(self):
        """
        Use the Localizer to detect obstacles and return their regions.
        Returns:
            List of (x, y) coordinates representing obstacle centers.
        """
        obstacle_particles = self.obstacle_localizer.updateParticles()
        print(f"Obstacle region center: {obstacle_particles}")
        return obstacle_particles

    def get_goal_location(self):
        """
        Use the Localizer to detect the goal location.
        Returns:
            Tuple (x, y) representing the goal location.
        """
        goal_x, goal_y = self.goal_localizer.updateParticles()
        print(f"Goal location: ({goal_x}, {goal_y})")
        return (goal_x, goal_y)

    def sample_free_space(self, obstacles, num_samples):
        """
        Sample points in free space while avoiding obstacle regions.
        Args:
            obstacles: List of obstacle centers.
            num_samples: Number of points to sample.
        Returns:
            List of (x, y) tuples representing sampled points.
        """
        free_space = []
        for _ in range(num_samples):
            while True:
                # Randomly sample a point
                x = random.uniform(0, self.display.width)
                y = random.uniform(0, self.display.height)

                # Check if the point is far from obstacles
                if all(self.euclidean_distance((x, y), obs) > 50 for obs in obstacles):
                    free_space.append((x, y))
                    break

        print(f"Sampled {len(free_space)} free space points.")
        return free_space

    def connect_samples(self, samples, obstacles, k_neighbors):
        """
        Connect sampled points using k-nearest neighbors.
        Args:
            samples: List of free space points.
            obstacles: List of obstacle centers.
            k_neighbors: Number of nearest neighbors to connect.
        Returns:
            A dictionary with nodes and edges.
        """
        nodes = samples
        edges = [[] for _ in samples]

        tree = KDTree(samples)

        for i, point in enumerate(samples):
            distances, neighbors = tree.query(point, k=k_neighbors + 1)
            for j, neighbor_idx in enumerate(neighbors[1:], start=1):  # Skip the point itself
                neighbor = samples[neighbor_idx]

                # Check if the edge intersects with obstacles
                if not self.is_edge_blocked(point, neighbor, obstacles):
                    edges[i].append(neighbor_idx)

        return {"nodes": nodes, "edges": edges}

    def is_edge_blocked(self, point1, point2, obstacles):
        """
        Check if a straight line between two points intersects any obstacles.
        Args:
            point1: Start of the line segment.
            point2: End of the line segment.
            obstacles: List of obstacle centers.
        Returns:
            True if blocked, False otherwise.
        """
        for obs in obstacles:
            if self.distance_to_line_segment(point1, point2, obs) < 50:  # Minimum safe distance
                return True
        return False

    @staticmethod
    def euclidean_distance(p1, p2):
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

    @staticmethod
    def distance_to_line_segment(point1, point2, obs):
        """
        Calculate the minimum distance from an obstacle to a line segment.
        """
        px, py = obs
        x1, y1 = point1
        x2, y2 = point2

        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return np.sqrt((px - x1)**2 + (py - y1)**2)

        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        nearest_x = x1 + t * dx
        nearest_y = y1 + t * dy

        return np.sqrt((px - nearest_x)**2 + (py - nearest_y)**2)
