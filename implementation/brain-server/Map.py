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
            "lower": np.array([5, 45, 60]),
            "upper": np.array([30, 255, 255])
        }
        goal_range = {
            "lower": np.array([115, 50, 30]),
            "upper": np.array([125, 255, 100])
        }

        # Create a mask for the obstacles (rectangle A)
        obstacle_mask = cv2.inRange(hsv_image, obstacle_range["lower"], obstacle_range["upper"])

        # Detect contours in the filtered obstacle mask
        contours, _ = cv2.findContours(obstacle_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Initialize storage for obstacles and weights
        self.obstacles = []
        self.obstacle_weights = {}

        max_area = 1000  # Maximum area for a single rectangle

        for contour in contours:
            # Calculate the bounding box and area of the contour
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h

            if area > 5:  # Ignore small noise-like regions
                # Create a filled mask of the contour
                contour_mask = np.zeros_like(obstacle_mask)
                cv2.drawContours(contour_mask, [contour], -1, 255, thickness=cv2.FILLED)

                # Process the contour to generate smaller bounding rectangles
                if area > max_area:
                    # Split the large filled rectangle
                    num_splits = int((area + max_area - 1) // max_area)
                    aspect_ratio = w / h
                    num_x_splits = max(1, int(np.sqrt(num_splits * aspect_ratio)))
                    num_y_splits = max(1, int(num_splits / num_x_splits))

                    split_width = w // num_x_splits
                    split_height = h // num_y_splits

                    for i in range(num_x_splits):
                        for j in range(num_y_splits):
                            split_x = x + i * split_width
                            split_y = y + j * split_height

                            # Adjust width/height for the last split if uneven
                            actual_width = split_width if i < num_x_splits - 1 else w - i * split_width
                            actual_height = split_height if j < num_y_splits - 1 else h - j * split_height

                            # Check if the rectangle overlaps with the actual mask
                            mask_region = contour_mask[split_y:split_y + actual_height, split_x:split_x + actual_width]
                            if cv2.countNonZero(mask_region) > 0:  # Check if any part of the rectangle is in the mask
                                split_rect = (split_x, split_y, actual_width, actual_height)

                                # Calculate weight for the sub-rectangle
                                split_area = actual_width * actual_height
                                split_weight = self.calculate_obstacle_weight(split_area)

                                # Store and visualize the sub-rectangles
                                self.obstacles.append(split_rect)
                                self.obstacle_weights[split_rect] = split_weight
                                self.display.draw_rectangle(f"obstacle_{split_rect}", split_x, split_y, actual_width, actual_height, weight=split_weight, color="#FFA500")
                else:
                    # If the rectangle is within the size limit, process it directly
                    mask_region = contour_mask[y:y + h, x:x + w]
                    if cv2.countNonZero(mask_region) > 0:  # Check if any part of the rectangle is in the mask
                        filled_rect = (x, y, w, h)

                        # Calculate weight based on area
                        weight = self.calculate_obstacle_weight(area)

                        # Store and visualize the rectangle
                        self.obstacles.append(filled_rect)
                        self.obstacle_weights[filled_rect] = weight
                        self.display.draw_rectangle(f"obstacle_{filled_rect}", x, y, w, h, weight=weight, color="#FFA500")

        # Detect goal
        goal_mask = cv2.inRange(hsv_image, goal_range["lower"], goal_range["upper"])
        contours, _ = cv2.findContours(goal_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            # Assuming the goal is the largest detected region
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)

            # Store the goal as a rectangle
            self.goal = (x, y, w, h)

            # Visualize the goal rectangle
            self.display.draw_rectangle("goal", x, y, w, h, weight=1.0, color="#0000FF")


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
        safe_distance = 100 * weight  # Scale safe distance based on weight
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
