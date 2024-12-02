import threading
import Camera
import Display
import Drone
import Map
import time
import numpy as np
from scipy.spatial import KDTree
import heapq  # For priority queue in A* algorithm

class Planner:
    def __init__(self, spheros):
        """
        Initialize the Planner class with the given spheros.
        Args:
            spheros (list): List of sphero dictionaries containing 'id' and 'color'.
        """
        self.display = Display.Display()  # Initialize Display
        self.camera = Camera.Camera(self.display)  # Pass Display to Camera

        # Capture an initial image to set dimensions
        self.camera.capture_image()

        # Start the display in a separate thread
        self.display_thread = threading.Thread(target=self.display.show, daemon=True)
        self.display_thread.start()

        # Initialize drones
        self.spheros = [
            Drone.Drone(self.display, sphero["id"], sphero["color"])
            for sphero in spheros
        ]

        self.map = Map.Map(self.display, self.spheros)
        self.roadmap = self.map.generate_prm()
        self.run_states()

        print(f"Planner initialized with Spheros: {spheros}\n")

    def stop(self):
        """
        Stop the display and release resources.
        """
        self.display.stop()  # Stop the display loop
        self.camera.release_camera()  # Release the camera resource

    def move_to_goal(self):
        """
        Navigate all Spheros towards the goal using PRM while avoiding collisions and obstacles.
        """
        goal = self.map.get_goal_location()

        while True:
            all_reached = True
            # Iterate over all Spheros
            for sphero in self.spheros:
                # Get the Sphero's current position
                current_position = sphero.get_position()

                # Recompute the roadmap and find the shortest path
                self.roadmap = self.map.generate_prm()
                path = self._find_path(current_position, goal)

                if path:
                    # Move Sphero to the next point in the path
                    next_point = path[1]  # The next point after the current position
                    sphero.move(next_point[0], next_point[1])

                    # Check if Sphero has reached the goal
                    if self._euclidean_distance(current_position, goal) > 10:  # Goal threshold
                        all_reached = False

            # Break the loop if all Spheros reach the goal
            if all_reached:
                print("All Spheros have reached the goal!")
                break

            # Delay to allow for smooth movement
            time.sleep(1)

    def _find_path(self, start, goal):
        """
        Find the shortest path from start to goal using A* algorithm on the PRM.
        Args:
            start (tuple): Starting position (x, y).
            goal (tuple): Goal position (x, y).
        Returns:
            List of (x, y) tuples representing the path.
        """
        nodes = self.roadmap["nodes"]
        edges = self.roadmap["edges"]

        start_idx = self._nearest_node(start, nodes)
        goal_idx = self._nearest_node(goal, nodes)

        # Priority queue for A*
        pq = []
        heapq.heappush(pq, (0, start_idx))

        came_from = {start_idx: None}
        cost_so_far = {start_idx: 0}

        while pq:
            current_cost, current_idx = heapq.heappop(pq)

            if current_idx == goal_idx:
                break

            for neighbor_idx in edges[current_idx]:
                new_cost = cost_so_far[current_idx] + self._euclidean_distance(
                    nodes[current_idx], nodes[neighbor_idx]
                )
                if neighbor_idx not in cost_so_far or new_cost < cost_so_far[neighbor_idx]:
                    cost_so_far[neighbor_idx] = new_cost
                    priority = new_cost + self._euclidean_distance(
                        nodes[neighbor_idx], nodes[goal_idx]
                    )
                    heapq.heappush(pq, (priority, neighbor_idx))
                    came_from[neighbor_idx] = current_idx

        # Reconstruct path
        current_idx = goal_idx
        path = []
        while current_idx is not None:
            path.append(nodes[current_idx])
            current_idx = came_from[current_idx]

        path.reverse()
        return path

    def _nearest_node(self, point, nodes):
        """
        Find the nearest node in the PRM to the given point.
        Args:
            point (tuple): The point (x, y).
            nodes (list): List of PRM nodes.
        Returns:
            int: Index of the nearest node.
        """
        tree = KDTree(nodes)
        _, idx = tree.query(point)
        return idx

    def _euclidean_distance(self, p1, p2):
        """
        Calculate the Euclidean distance between two points.
        """
        return np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
