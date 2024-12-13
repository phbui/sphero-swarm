import numpy as np
import cv2
import random
from sklearn.neighbors import KDTree
from color_ranges import obstacle_range, goal_range

class Map:
    def __init__(self, display):
        """
        Initialize the Map class.
        Args:
            display: Reference to the Display class for visualization.
        """
        self.display = display  # Reference to a display object for visualization
        self.obstacles = []  # List to store obstacle rectangles
        self.goal = None  # Variable to store the goal region
        self.nodes = []  # List of PRM nodes
        self.edges = []  # List of PRM edges
        self.kdtree = None

    def calculate_obstacle_weight(self, area):
        """
        Calculate a weight for an obstacle based on its area.
        Args:
            area: The area of the obstacle.
        Returns:
            A weight value.
        """
        # Normalize the area to a range (e.g., between 0.1 and 1.0)
        max_area = 1000 
        min_weight = 0.1
        max_weight = 1.0

        # Calculate weight as a normalized value
        weight = min_weight + (max_weight - min_weight) * min(area, max_area) / max_area
        return weight

    def process_image(self):
        """
        Process the input image to detect obstacles and the goal.
        """
        image = self.display.get_image()  # Get the current image from the display

        # Convert the image to HSV color space for easier color detection
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Create a mask for detecting obstacles
        obstacle_mask = cv2.inRange(hsv_image, obstacle_range["lower"], obstacle_range["upper"])
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        obstacle_mask = cv2.morphologyEx(obstacle_mask, cv2.MORPH_CLOSE, kernel)    
        obstacle_mask = cv2.erode(obstacle_mask, kernel, iterations=1) 
        obstacle_mask = cv2.dilate(obstacle_mask, kernel, iterations=1)

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
                temp_mask = obstacle_mask[y:y + h, x:x + w].copy()
                full_mask = np.zeros_like(obstacle_mask)
                full_mask[y:y+h, x:x+w] = temp_mask
                contour_mask = full_mask

                if area > max_area:
                    # Split large rectangles into smaller regions
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

    def generate_prm(self, num_nodes=100, initial_radius=100, max_radius=500):
        """
        Generate a probabilistic roadmap (PRM) for path planning.
        Args:
            num_nodes: Number of nodes to generate for the roadmap.
            initial_radius: Starting distance to connect nodes.
            max_radius: Maximum distance to connect nodes.
        """
        print("Generating map...")
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
            # Debug Nodes
            #self.display.draw_label(f"goal_label", goal_center[1], goal_center[0], f"y:{goal_center[1]},x:{goal_center[0]}", color="#0000FF")
        else:
            print("No goal detected.")
            return

        if not self.obstacles:
            print("No obstacles detected.")

        # Generate random nodes avoiding obstacles
        max_attempts = 1000
        attempts = 0
        while len(self.nodes) < num_nodes and attempts < max_attempts:
            x, y = random.randint(0, width - 1), random.randint(0, height - 1)
            if not any(self.is_near_obstacle_rect(x, y, rect) for rect in self.obstacles):
                self.nodes.append((x, y))
            attempts += 1

        # Connect nodes starting from the goal
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
                                connections += 1
                if connections < 3:
                    current_radius += 50

        # Prune nodes and edges not connected to the goal
        self._prune_unconnected_nodes()

        # Draw the remaining nodes and edges
        for x, y in self.nodes:
            self.display.draw_point(f"node_{x}_{y}", y, x, weight=0.1, color="#00FF00")
            # Debug Nodes
            #self.display.draw_label(f"node_{x}_{y}_label", y, x, f"y:{y},x:{x}", color="#00FF00")


        for (x1, y1), (x2, y2) in self.edges:
            self.display.draw_line(f"edge_{x1}_{y1}_{x2}_{y2}", (y1, x1), (y2, x2), weight=0.1, color="#000000")

            if self.nodes:
                self.kdtree = KDTree(self.nodes)
            else:
                print("No PRM nodes available to build KDTree.")

    def is_on_obstacle_near_boundary(self, y, x, boundary_threshold=50):
        """
        Check if the given point (y, x) lies on an obstacle that is near the edge of the screen.
        Args:
            y, x: The coordinates of the point to check.
            boundary_threshold: The distance threshold from the screen edge to consider "near the edge."
        Returns:
            True if the point is on an obstacle located near the screen boundary, False otherwise.
        """
        # Get the dimensions of the display
        height, width = self.display.height, self.display.width

        for rect in self.obstacles:
            rx, ry, rw, rh = rect
            # Check if the obstacle is near the boundary of the screen
            near_left_edge = (rx <= boundary_threshold)
            near_right_edge = (rx + rw >= width - boundary_threshold)
            near_top_edge = (ry <= boundary_threshold)
            near_bottom_edge = (ry + rh >= height - boundary_threshold)

            if near_left_edge or near_right_edge or near_top_edge or near_bottom_edge:
                # Check if the point (x, y) lies inside the obstacle rectangle
                if rx <= x <= rx + rw and ry <= y <= ry + rh:
                    return True

        return False


    def find_closest_node(self, position):
        """
        Find the closest node to a given position based on x and y coordinates using KDTree.
        Args:
            position: Target position as a tuple.
        Returns:
            Closest node as a tuple.
        """
        if not hasattr(self, "kdtree") or not self.kdtree:
            # Build KDTree if not already built
            self.kdtree = KDTree(self.nodes)

        # Reshape the position to 2D array as required by KDTree
        position = np.array(position).reshape(1, -1)

        # Query the KDTree for the nearest node
        _, idx = self.kdtree.query(position)

        # Ensure the index is a native Python integer
        return self.nodes[int(idx)]


    def _prune_unconnected_nodes(self):
        """
        Prune nodes and edges that are not connected to the goal node.
        """
        if not self.nodes or not self.edges:
            return

        # Use DFS to find all reachable nodes from the goal
        goal_node = self.nodes[0]  # Goal node is the first node added
        reachable = set()
        stack = [goal_node]

        while stack:
            current_node = stack.pop()
            if current_node not in reachable:
                reachable.add(current_node)
                # Find neighbors of the current node
                for edge in self.edges:
                    if current_node == edge[0] and edge[1] not in reachable:
                        stack.append(edge[1])
                    elif current_node == edge[1] and edge[0] not in reachable:
                        stack.append(edge[0])

        # Remove nodes and edges not in the reachable set
        self.nodes = [node for node in self.nodes if node in reachable]
        self.edges = [edge for edge in self.edges if edge[0] in reachable and edge[1] in reachable]

    def is_near_obstacle_rect(self, x, y, rect):
        """
        Check if a node is too close to a rectangular obstacle.
        Args:
            x, y: Node coordinates.
            rect: Tuple (rx, ry, rw, rh) representing the rectangle.
        Returns:
            True if the node is near the rectangle, False otherwise.
        """
        rx, ry, rw, rh = rect
        buffer = 10  # Buffer distance around the rectangle
        return rx - buffer <= x <= rx + rw + buffer and ry - buffer <= y <= ry + rh + buffer

    def check_collision_with_rects(self, point1, point2):
        """
        Check if a line segment between two points intersects any rectangular obstacles.
        Args:
            point1: Tuple (x1, y1) representing the start point of the line segment.
            point2: Tuple (x2, y2) representing the end point of the line segment.
        Returns:
            True if the line segment intersects any obstacle, False otherwise.
        """
        for rect in self.obstacles:
            if self.line_intersects_rect(point1, point2, rect):
                return True
        return False

    def line_intersects_rect(self, p1, p2, rect):
        """
        Check if a line segment intersects a rectangle.
        Args:
            p1, p2: Endpoints of the line segment.
            rect: Tuple (rx, ry, rw, rh) representing the rectangle.
        Returns:
            True if the line segment intersects the rectangle, False otherwise.
        """
        rx, ry, rw, rh = rect
        rect_edges = [
            ((rx, ry), (rx + rw, ry)),  # Top edge
            ((rx, ry), (rx, ry + rh)),  # Left edge
            ((rx + rw, ry), (rx + rw, ry + rh)),  # Right edge
            ((rx, ry + rh), (rx + rw, ry + rh))   # Bottom edge
        ]
        for edge in rect_edges:
            if self.line_segments_intersect(p1, p2, edge[0], edge[1]):
                return True
        return False

    def line_segments_intersect(self, p1, p2, q1, q2):
        """
        Check if two line segments intersect.
        Args:
            p1, p2: Endpoints of the first line segment.
            q1, q2: Endpoints of the second line segment.
        Returns:
            True if the line segments intersect, False otherwise.
        """
        def ccw(a, b, c):
            return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])

        return ccw(p1, q1, q2) != ccw(p2, q1, q2) and ccw(p1, p2, q1) != ccw(p1, p2, q2)
