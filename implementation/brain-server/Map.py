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
        try:
            self.display = display  # Reference to a display object for visualization
            self.obstacles = []  # List to store obstacle rectangles
            self.goal = None  # Variable to store the goal region
            self.nodes = []  # List of PRM nodes
            self.edges = []  # List of PRM edges
        except Exception as e:
            print(f"Error initializing Map: {e}")

    def calculate_obstacle_weight(self, area):
        """
        Calculate a weight for an obstacle based on its area.
        Args:
            area: The area of the obstacle.
        Returns:
            A weight value.
        """
        try:
            max_area = 1000 
            min_weight = 0.1
            max_weight = 1.0

            # Calculate weight as a normalized value
            weight = min_weight + (max_weight - min_weight) * min(area, max_area) / max_area
            return weight
        except Exception as e:
            print(f"Error in `calculate_obstacle_weight`: {e}")
            return 0

    def process_image(self):
        """
        Process the input image to detect obstacles and the goal.
        """
        try:
            image = self.display.get_image()  # Get the current image from the display

            # Convert the image to HSV color space for easier color detection
            hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

            # Define color ranges for detecting obstacles and the goal
            obstacle_range = {
                "lower": np.array([5, 45, 60]),
                "upper": np.array([30, 255, 255])
            }
            goal_range = {
                "lower": np.array([115, 50, 30]),
                "upper": np.array([125, 255, 100])
            }

            # Create a mask for detecting obstacles
            obstacle_mask = cv2.inRange(hsv_image, obstacle_range["lower"], obstacle_range["upper"])

            # Detect contours in the obstacle mask
            contours, _ = cv2.findContours(obstacle_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Initialize storage for obstacles and weights
            self.obstacles = []
            self.obstacle_weights = {}

            max_area = 1000  # Maximum allowed area for an obstacle

            for contour in contours:
                # Calculate the bounding box and area of each contour
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h

                if area > 100:  # Ignore small noise-like regions
                    # Create a filled mask for the current contour
                    contour_mask = np.zeros_like(obstacle_mask)
                    cv2.drawContours(contour_mask, [contour], -1, 255, thickness=cv2.FILLED)

                    if area > max_area:
                        # Split large rectangles into smaller regions
                        self._split_large_obstacle(contour_mask, x, y, w, h, area, max_area)
                    else:
                        # Process rectangles within size limits
                        mask_region = contour_mask[y:y + h, x:x + w]
                        if cv2.countNonZero(mask_region) > 0:
                            filled_rect = (x, y, w, h)
                            weight = self.calculate_obstacle_weight(area)
                            self.obstacles.append(filled_rect)
                            self.obstacle_weights[filled_rect] = weight
                            self.display.draw_rectangle(f"obstacle_{filled_rect}", x, y, w, h, weight=weight, color="#FFA500")

            # Detect the goal region
            goal_mask = cv2.inRange(hsv_image, goal_range["lower"], goal_range["upper"])
            contours, _ = cv2.findContours(goal_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                # Use the largest detected region as the goal
                largest_contour = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(largest_contour)
                self.goal = (x, y, w, h)
                self.display.draw_rectangle("goal", x, y, w, h, weight=1.0, color="#0000FF")
        except Exception as e:
            print(f"Error in `process_image`: {e}")

    def _split_large_obstacle(self, contour_mask, x, y, w, h, area, max_area):
        """
        Split a large obstacle into smaller regions.
        Args:
            contour_mask: Mask of the contour to be split.
            x, y: Top-left coordinates of the bounding box.
            w, h: Width and height of the bounding box.
            area: Area of the bounding box.
            max_area: Maximum allowed area for a single region.
        """
        try:
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

                    # Adjust dimensions for uneven splits
                    actual_width = split_width if i < num_x_splits - 1 else w - i * split_width
                    actual_height = split_height if j < num_y_splits - 1 else h - j * split_height

                    # Check overlap with the original contour mask
                    mask_region = contour_mask[split_y:split_y + actual_height, split_x:split_x + actual_width]
                    if cv2.countNonZero(mask_region) > 0:
                        split_rect = (split_x, split_y, actual_width, actual_height)
                        split_area = actual_width * actual_height
                        split_weight = self.calculate_obstacle_weight(split_area)

                        # Store and visualize the split rectangle
                        self.obstacles.append(split_rect)
                        self.obstacle_weights[split_rect] = split_weight
                        self.display.draw_rectangle(f"obstacle_{split_rect}", split_x, split_y, actual_width, actual_height, weight=split_weight, color="#FFA500")
        except Exception as e:
            print(f"Error in `_split_large_obstacle`: {e}")

    def generate_prm(self, num_nodes=200, initial_radius=100, max_radius=1000):
        """
        Generate a probabilistic roadmap (PRM) for path planning.
        Args:
            num_nodes: Number of nodes to generate for the roadmap.
            initial_radius: Starting distance to connect nodes.
            max_radius: Maximum distance to connect nodes.
        """
        try:
            self.process_image()  # Process the image to detect obstacles and the goal

            # Initialize nodes and edges for the PRM
            self.nodes = []
            self.edges = []

            height, width = self.display.height, self.display.width

            if self.goal:
                # Add the goal center as a node
                gx, gy, gw, gh = self.goal
                goal_center = (gx + gw // 2, gy + gh // 2)
                self.nodes.append(goal_center)
                self.display.draw_point("goal_node", goal_center[1], goal_center[0], weight=0.2, color="#0000FF")
            else:
                print("No goal detected.")

            if not self.obstacles:
                print("No obstacles detected.")

            # Generate random nodes avoiding obstacles
            max_attempts = 1000
            attempts = 0
            while len(self.nodes) < num_nodes and attempts < max_attempts:
                x, y = random.randint(0, width - 1), random.randint(0, height - 1)
                if not any(self.is_near_obstacle_rect(x, y, rect) for rect in self.obstacles):
                    self.nodes.append((x, y))
                    self.display.draw_point(f"node_{x}_{y}", y, x, weight=0.1, color="#00FF00")
                attempts += 1

            # Connect nodes within a dynamic radius
            for i, (x1, y1) in enumerate(self.nodes):
                current_radius = initial_radius
                connections = 0

                while connections < 3 and current_radius <= max_radius:
                    for j, (x2, y2) in enumerate(self.nodes):
                        if i != j:
                            distance = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                            if distance <= current_radius and not self.check_collision_with_rects((x1, y1), (x2, y2)):
                                edge = ((x1, y1), (x2, y2))
                                if edge not in self.edges:
                                    self.edges.append(edge)
                                    self.display.draw_line(f"edge_{i}_{j}", (y1, x1), (y2, x2), weight=0.1, color="#000000")
                                    connections += 1
                    if connections < 5:
                        current_radius += 50

            print("Map generated.")
        except Exception as e:
            print(f"Error in `generate_prm`: {e}")
