import numpy as np
import cv2
import random
class Map:
    def __init__(self, display):
        """
        Initialize the Map class.
        Args:
            display: Reference to the Display class for visualization.
        """
        self.display = display
        self.obstacles = []
        self.goal = None
        self.nodes = []
        self.edges = []

    def process_image(self):
        """
        Process the input image to detect obstacles and the goal.
        """
        image = self.display.get_image()
        # Convert the image to HSV color space
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Define color ranges for obstacles and goal
        obstacle_range = {
            "lower": np.array([15, 45, 60]),
            "upper": np.array([30, 255, 255])
        }
        goal_range = {
            "lower": np.array([130, 50, 50]),
            "upper": np.array([160, 255, 255])
        }

        # Detect obstacles
        obstacle_mask = cv2.inRange(hsv_image, obstacle_range["lower"], obstacle_range["upper"])
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(obstacle_mask, connectivity=8)

        self.obstacles = []
        for i in range(1, num_labels):  # Start from 1 to skip the background
            x, y, w, h, area = stats[i]
            if area > 0.1:  # Filter out very small regions to avoid tiny noise clusters
                obstacle_center = (x + w // 2, y + h // 2)
                self.obstacles.append(obstacle_center)
                # Draw larger obstacle region as a circle or rectangle
                self.display.draw(f"obstacle_{obstacle_center}", obstacle_center[1], obstacle_center[0], weight=(0.25), color="#FFA500")

        # Detect goal
        goal_mask = cv2.inRange(hsv_image, goal_range["lower"], goal_range["upper"])
        goal_points = cv2.findNonZero(goal_mask)
        if goal_points is not None:
            # Assuming the goal is a single region, take the centroid as the goal position
            goal_coords = np.mean(goal_points, axis=0)[0]
            self.goal = (int(goal_coords[0]), int(goal_coords[1]))
            # Draw the goal on the display
            self.display.draw("goal", self.goal[1], self.goal[0], weight=1.0, color="#0000FF")

    def generate_prm(self, num_nodes=100, connection_radius=50):
        """
        Generate a probabilistic roadmap (PRM) for path planning.
        Args:
            num_nodes: Number of nodes to generate for the roadmap.
            connection_radius: Maximum distance to connect nodes.
        """
        # Process the image to detect obstacles and goal
        self.process_image()

        height, width = self.display.height, self.display.width

        # Generate random nodes
        for _ in range(num_nodes):
            x, y = random.randint(0, width - 1), random.randint(0, height - 1)

            # Check if the node is in an obstacle region
            if any(abs(x - ox) < 5 and abs(y - oy) < 5 for (ox, oy) in self.obstacles):
                continue

            self.nodes.append((x, y))

        # Connect nodes based on distance
        for i, (x1, y1) in enumerate(self.nodes):
            for j, (x2, y2) in enumerate(self.nodes):
                if i != j:
                    distance = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                    if distance <= connection_radius:
                        self.edges.append(((x1, y1), (x2, y2)))
