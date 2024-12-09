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

    def calculate_obstacle_weight(self, area):
        """
        Calculate a weight for an obstacle based on its area.
        Args:
            area: The area of the obstacle.
        Returns:
            A weight value.
        """
        # Normalize the area to a range (e.g., between 0.1 and 1.0)
        max_area = 1000  # Adjust based on expected maximum obstacle size
        min_weight = 0.1
        max_weight = 1.0

        # Calculate weight as a normalized value
        weight = min_weight + (max_weight - min_weight) * min(area, max_area) / max_area
        return weight


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
            "lower": np.array([115, 50, 30]),
            "upper": np.array([125, 255, 100])
        }

        # Detect obstacles
        obstacle_mask = cv2.inRange(hsv_image, obstacle_range["lower"], obstacle_range["upper"])
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(obstacle_mask, connectivity=8)

        self.obstacles = []
        self.obstacle_weights = {} 
    
        for i in range(1, num_labels):  # Start from 1 to skip the background
            x, y, w, h, area = stats[i]
            if area > 0.1:  # Filter out very small regions to avoid tiny noise clusters
                obstacle_center = (x + w // 2, y + h // 2)
                weight = self.calculate_obstacle_weight(area)  # Calculate weight based on area
                self.obstacles.append(obstacle_center)
                self.obstacle_weights[obstacle_center] = weight
                self.obstacles.append(obstacle_center)
                # Draw larger obstacle region as a circle or rectangle
                self.display.draw_point(f"obstacle_{obstacle_center}", obstacle_center[1], obstacle_center[0],  weight=weight, color="#FFA500")

        # Detect goal
        goal_mask = cv2.inRange(hsv_image, goal_range["lower"], goal_range["upper"])
        goal_points = cv2.findNonZero(goal_mask)
        if goal_points is not None:
            # Assuming the goal is a single region, take the centroid as the goal position
            goal_coords = np.mean(goal_points, axis=0)[0]
            self.goal = (int(goal_coords[0]), int(goal_coords[1]))
            # Draw the goal on the display
            self.display.draw_point("goal", self.goal[1], self.goal[0], weight=1.0, color="#0000FF")

    def generate_prm(self, num_nodes=100, initial_radius=100, max_radius=1000):
        """
        Generate a probabilistic roadmap (PRM) for path planning.
        Args:
            num_nodes: Number of nodes to generate for the roadmap.
            initial_radius: Starting distance to connect nodes.
            max_radius: Maximum distance to connect nodes.
        """
        # Process the image to detect obstacles and goal
        self.process_image()

        height, width = self.display.height, self.display.width

        # Add goal as the first node if detected
        if self.goal:
            self.nodes.append(self.goal)
            self.display.draw_point("goal_node", self.goal[1], self.goal[0], weight=0.2, color="#0000FF")

        # Generate random nodes
        for _ in range(num_nodes):
            x, y = random.randint(0, width - 1), random.randint(0, height - 1)

            # Penalize nodes based on proximity to obstacles
            if any(self.is_near_obstacle(x, y, ox, oy, self.obstacle_weights[(ox, oy)]) for (ox, oy) in self.obstacles):
                continue

            self.nodes.append((x, y))
            self.display.draw_point(f"node_{x}_{y}", y, x, weight=0.1, color="#00FF00")

        # Dynamically adjust the connection radius to ensure at least 5 connections per node
        for i, (x1, y1) in enumerate(self.nodes):
            current_radius = initial_radius
            connections = 0

            while connections < 5 and current_radius <= max_radius:
                for j, (x2, y2) in enumerate(self.nodes):
                    if i != j:
                        distance = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                        if distance <= current_radius and not self.check_collision((x1, y1), (x2, y2)):
                            edge = ((x1, y1), (x2, y2))
                            if edge not in self.edges:  # Prevent duplicate edges
                                self.edges.append(edge)
                                self.display.draw_line(f"edge_{i}_{j}", (y1, x1), (y2, x2), weight=0.1, color="#000000")
                                connections += 1
                if connections < 10:
                    current_radius += 50  # Increase radius if fewer than 5 connections

    def is_near_obstacle(self, x, y, ox, oy, weight):
        """
        Check if a node is too close to an obstacle, considering its weight.
        Args:
            x, y: Node coordinates.
            ox, oy: Obstacle coordinates.
            weight: Weight of the obstacle.
        Returns:
            True if the node is near the obstacle, False otherwise.
        """
        safe_distance = 250 * weight  # Scale safe distance based on weight
        return np.sqrt((x - ox) ** 2 + (y - oy) ** 2) < safe_distance

    def check_collision(self, point1, point2):
        """
        Check if a line segment between two points intersects any obstacles.
        Args:
            point1, point2: Endpoints of the line segment.
        Returns:
            True if the line segment intersects any obstacle, False otherwise.
        """
        for (ox, oy) in self.obstacles:
            distance = self.point_to_segment_distance(point1, point2, (ox, oy))
            if distance < 10:  # Collision threshold
                return True
        return False

    def point_to_segment_distance(self, p1, p2, p):
        """
        Calculate the minimum distance from a point to a line segment.
        Args:
            p1, p2: Endpoints of the line segment.
            p: The point to calculate the distance to.
        Returns:
            The minimum distance from the point to the line segment.
        """
        x1, y1 = p1
        x2, y2 = p2
        px, py = p

        # Compute the projection of the point onto the line segment
        line_mag = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if line_mag < 1e-6:  # Avoid division by zero
            return np.sqrt((px - x1) ** 2 + (py - y1) ** 2)

        u = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / (line_mag ** 2)
        u = max(0, min(1, u))  # Clamp u to the range [0, 1]

        # Compute the closest point on the line segment
        closest_x = x1 + u * (x2 - x1)
        closest_y = y1 + u * (y2 - y1)

        # Compute the distance from the point to the closest point
        return np.sqrt((px - closest_x) ** 2 + (py - closest_y) ** 2)
