import numpy as np
import heapq
import Localizer
import math

class Drone:
    def __init__(self, planner, camera, display, sphero_id, sphero_color, map):
        """
        Initialize a Drone (Sphero) with its display, ID, and color.
        Args:
            camera: Camera instance for localization.
            display: The display instance for visualization.
            sphero_id: Unique identifier for the Sphero.
            sphero_color: Color used for identifying the Sphero.
            map: Reference to the Map instance containing PRM and obstacles.
        """
        try:
            self.planner = planner
            self.display = display
            self.sphero_id = sphero_id
            self.sphero_color = sphero_color
            print(f"Sphero Initialized: {sphero_id}")
            self.localizer = Localizer.Localizer(camera, display, sphero_color, 500)
            self.map = map
            if len(self.map.goal) == 4:
                gx, gy, gw, gh = self.map.goal
                self.goal = (gx + gw // 2, gy + gh // 2)
            print(f"Goal at: y:{self.goal[1]}, x:{self.goal[0]}")
            self.goal_node = self.map.find_closest_node(self.goal)

            self.current_y = -1
            self.current_x = -1
            self.current_confidence = 0.5

            self.last_attempt = None  # Store the last visited point
            self.last_location = None

            # Kalman filter variables
            self.angle = -1
            self.speed = -1
            self.x_kf = None
            self.P_kf = None
            self.F = None
            self.H = None
            self.Q = None
            self.R_base = None
            self.kf_initialized = False
            self.dt = 2.0  # Time interval between updates (assumed)

            # State Machine for the Drone
            self.states = [
                {
                    "state": "move_to_goal",
                    "description": "Sphero navigates towards the goal.",
                    "transitions": [
                        {
                            "condition": "Reached goal threshold distance",
                            "next_state": "reaching_goal"
                        }
                    ]
                },
                {
                    "state": "interact",
                    "description": "Sphero executes interaction behavior.",
                    "transitions": [
                        {
                            "condition": "Interaction complete",
                            "next_state": None
                        }
                    ]
                }
            ]
            self.current_state_index = 0  # Start with "move_to_goal"
        except Exception as e:
            print(f"Error initializing Drone: {e}")

    def _init_kf(self, y, x):
        """
        Initialize the Kalman filter with the initial position and zero velocity.
        State: [y, x, vy, vx]
        """
        self.x_kf = np.array([[y],
                              [x],
                              [0.0],
                              [0.0]])
        self.P_kf = np.eye(4)*1.0

        self.F = np.array([[1, 0, self.dt, 0],
                           [0, 1, 0, self.dt],
                           [0, 0, 1,    0],
                           [0, 0, 0,    1]], dtype=float)

        self.H = np.array([[1, 0, 0, 0],
                           [0, 1, 0, 0]], dtype=float)

        q = 1e-2
        dt = self.dt
        self.Q = q * np.array([[dt**4/4, 0,         dt**3/2, 0        ],
                               [0,       dt**4/4,   0,       dt**3/2  ],
                               [dt**3/2, 0,         dt**2,   0        ],
                               [0,       dt**3/2,   0,       dt**2    ]])

        r = 0.1
        self.R_base = np.array([[r,   0],
                                [0,   r]], dtype=float)

        self.kf_initialized = True

    def _kf_predict(self):
        self.x_kf = self.F @ self.x_kf
        self.P_kf = self.F @ self.P_kf @ self.F.T + self.Q

    def _kf_update(self, z):
        # Scale R by inverse of confidence: higher confidence -> smaller R
        eps = 1e-6
        scale = 1.0 / (self.current_confidence + eps)
        R = self.R_base * scale

        z = np.array([[z[0]],
                      [z[1]]])
        y = z - self.H @ self.x_kf
        S = self.H @ self.P_kf @ self.H.T + R
        K = self.P_kf @ self.H.T @ np.linalg.inv(S)
        self.x_kf = self.x_kf + K @ y
        I = np.eye(len(self.P_kf))
        self.P_kf = (I - K @ self.H) @ self.P_kf
    
    def _calculate_corrected_parameters(self, target_position):
        """
        Perform a full predict-update cycle with the Kalman filter and calculate angle & timing.
        Also implements a stuck detection heuristic.
        """
        self._kf_predict()
        self._kf_update((self.current_y, self.current_x))

        # Extract angle and speed from updated KF state
        vy = self.x_kf[2,0]
        vx = self.x_kf[3,0]
        speed = math.sqrt(vx**2 + vy**2)
        angle = math.degrees(math.atan2(vx, vy)) % 360

        # Calculate timing based on speed
        delta_y_target = target_position[0] - self.x_kf[0,0]
        delta_x_target = target_position[1] - self.x_kf[1,0]
        distance_to_target = math.sqrt(delta_x_target**2 + delta_y_target**2)
        
        speed_adj = speed + 1e-6
        timing = distance_to_target / speed_adj

        if timing > 5:
            timing = 5  

        # Heuristic: Check if stuck
        if (self.last_location is not None 
            and self._position_unchanged(self.last_location, (self.current_y, self.current_x))
            and self._angle_unchanged(self.angle, angle)
            and self.map.is_on_obstacle_near_boundary(self.current_x, self.current_y)):
            
            # Turn around or choose a new angle
            angle = (angle + 180) % 360
            print("Stuck detected. Turning around.")

        self.angle = angle
        self.speed = speed

        # Update state references
        self.last_location = (self.current_y, self.current_x)
        self.last_attempt = target_position

        return angle, timing

    def calculate_movement_parameters(self, target_position):
        """
        Calculate the angle and timing needed to reach the target position with a proper Kalman filter approach.

        Args:
            target_position: Tuple (y, x) representing the target position.

        Returns:
            tuple: (corrected_angle, timing)
        """
        try:
            if self.last_location is None:
                return self._initialize_state(target_position)

            if self.angle == -1 or self.speed == -1:
                return self._initialize_angle_and_speed(target_position)

            return self._calculate_corrected_parameters(target_position)

        except ZeroDivisionError:
            print("Error: Division by zero occurred in timing calculation.")
            return self.angle, 2  # Fallback timing
        except Exception as e:
            print(f"Unexpected error in calculate_movement_parameters: {e}")
            return self.angle, 2  # Fallback timing

    def _initialize_state(self, target_position):
        """
        Handle the initial state where no previous data exists.
        Initialize the KF with the current position.
        """
        self.last_location = (self.current_y, self.current_x)
        self.last_attempt = target_position

        if not self.kf_initialized:
            self._init_kf(self.current_y, self.current_x)

        # From the KF state (initially zero velocity), compute angle and speed
        vy = self.x_kf[2,0]
        vx = self.x_kf[3,0]
        angle = math.degrees(math.atan2(vx, vy)) % 360
        speed = math.sqrt(vx**2 + vy**2)

        self.angle = angle
        self.speed = speed

        # Just return some initial guess for timing since no movement yet
        return angle, 2

    def _initialize_angle_and_speed(self, target_position):
        """
        After the second movement, use the second measurement to update the KF and get a better estimate.
        """
        if not self.kf_initialized:
            # In case it wasn't done before
            self._init_kf(self.last_location[0], self.last_location[1])

        # Predict then update with the new measurement (current position)
        self._kf_predict()
        self._kf_update((self.current_y, self.current_x))

        # Extract angle and speed from the KF
        vy = self.x_kf[2,0]
        vx = self.x_kf[3,0]
        observed_speed = math.sqrt(vx**2 + vy**2)
        observed_angle = math.degrees(math.atan2(vx, vy)) % 360

        # Calculate timing based on observed speed
        delta_y_target = target_position[0] - self.x_kf[0,0]
        delta_x_target = target_position[1] - self.x_kf[1,0]
        distance_to_target = math.sqrt(delta_x_target**2 + delta_y_target**2)
        
        speed_adj = observed_speed + 1e-6
        timing = distance_to_target / speed_adj

        if timing > 5:
            timing = 5

        self.angle = observed_angle
        self.speed = observed_speed

        # Update last known positions
        self.last_location = (self.current_y, self.current_x)
        self.last_attempt = target_position

        return self.angle, timing

    def _position_unchanged(self, prev_pos, current_pos, threshold=5.0):
        py, px = prev_pos
        cy, cx = current_pos
        dist = math.sqrt((cx - px)**2 + (cy - py)**2)
        return dist < threshold

    def _angle_unchanged(self, prev_angle, current_angle, tolerance=5.0):
        return abs((current_angle - prev_angle) % 360) < tolerance

    def _calculate_angle(self, start, end):
        """
        Calculate the angle from start to end.
        """
        delta_y = end[0] - start[0]
        delta_x = end[1] - start[1]
        return math.degrees(math.atan2(delta_x, delta_y))

    def get_position(self):
        """
        Get the current position of the Sphero using localization.
        Returns:
            Tuple (y, x) representing the current position.
        """
        try:
            self.current_y, self.current_x, self.current_confidence = self.localizer.updateParticles()
        except Exception as e:
            print(f"Error getting position: {e}")
            return None

    def move(self, current_x, current_y, target_x, target_y):
        """
        Move the Sphero to the target position.
        Args:
            current_x: Current x-coordinate.
            current_y: Current y-coordinate.
            target_x: Target x-coordinate.
            target_y: Target y-coordinate.
        """
        try:
            # Draw a point at the current position
            point_id = f"{self.sphero_id}"
            self.display.draw_point(
                point_id,
                current_y, 
                current_x, 
                0.5,
                self.sphero_color
            )

            # Draw a line from the current position to the target position
            line_id = f"{self.sphero_id}-vector"
            self.display.draw_line(
                id=line_id,
                point1=(current_y, current_x),
                point2=(target_y, target_x),
                weight=2,
                color=self.sphero_color
            )

            # Draw a point at the target position
            point_id = f"{self.sphero_id}-point"
            self.display.draw_point(
                point_id,
                target_y, 
                target_x, 
                0.25,
                self.sphero_color
            )

            # Update the last visited point
            self.last_attempt = (target_y, target_x)
            self.last_location = (current_y, current_x)
        except Exception as e:
            print(f"Error during move: {e}")

    def execute_state(self):
        """
        Execute the current state of the Sphero.
        """
        try:
            current_state = self.states[self.current_state_index]
            state_name = current_state["state"]
            print(f"Sphero [{self.sphero_id}] executing state: {state_name}")

            self.get_position()

            if state_name == "move_to_goal":
                self._move_to_goal()
            elif state_name == "interact":
                self._interact()
        except Exception as e:
            print(f"Error executing state: {e}")

    def _move_to_goal(self):
        """
        Navigate towards the goal and send movement updates.
        """
        try:
            if not self.goal:
                #print(f"Sphero [{self.sphero_id}]: Goal is not set!")
                return
            
            print(f"Sphero [{self.sphero_id}] at: y:{self.current_y}, x:{self.current_x}")

            if self.reached_goal():
                self._transition_to_state("interact")
            else:
                self.submit_trajectory()
        except Exception as e:
            print(f"Error in _move_to_goal: {e}")

    def reached_goal(self):
        """
        Check if the Sphero is within threshold distance of the goal.
        """
        try:
            if self._euclidean_distance((self.current_x, self.current_y), self.goal) <= 100:
                print(f"Sphero [{self.sphero_id}] precisely aligned with the goal.")
                return True
        except Exception as e:
            print(f"Error in _reaching_goal: {e}")
        print(f"Sphero [{self.sphero_id}] not at goal.")
        return False

    def _interact(self):
        """
        Execute interaction behavior.
        """
        try:
            print(f"Sphero [{self.sphero_id}] interacting.")
            # Add specific interaction logic here
            print(f"Sphero [{self.sphero_id}] interaction complete.")
        except Exception as e:
            print(f"Error in _interact: {e}")

    def _transition_to_state(self, next_state_name):
        """
        Transition to the specified state.
        Args:
            next_state_name: Name of the state to transition to.
        """
        try:
            for i, state in enumerate(self.states):
                if state["state"] == next_state_name:
                    self.current_state_index = i
                    print(f"Sphero [{self.sphero_id}] transitioning to state: {next_state_name}")
                    return
        except Exception as e:
            print(f"Error transitioning state: {e}")

    def _find_path(self, start):
        """
        Find the shortest path from start to goal using the PRM nodes.
        Args:
            start: Starting position as a tuple (x, y).
        Returns:
            List of tuples representing the path.
        """
        try:
            if not self.map.nodes or len(self.map.nodes) == 0:
                print(f"Sphero [{self.sphero_id}] has no PRM nodes available!")
                return []

            # Find the closest PRM node to the start and the goal using KDTree
            closest_node = self.map.find_closest_node((start[1], start[0]))
            goal_node = self.map.find_closest_node(self.goal)

            if not closest_node or not goal_node:
                print(f"Sphero [{self.sphero_id}] could not find valid nodes.")
                return []

            # Get indices of the closest nodes in the PRM node list
            start_idx = self.map.nodes.index(closest_node)
            goal_idx = self.map.nodes.index(goal_node)
            print(f"Closest Node to Start: y:{closest_node[1]}, x: {closest_node[0]}")
            print(f"Closest Node to Goal: y:{goal_node[1]}, x: {goal_node[0]}")

            # Initialize A* search
            pq = []
            heapq.heappush(pq, (0, start_idx))
            came_from = {start_idx: None}
            cost_so_far = {start_idx: 0}

            # A* Algorithm
            while pq:
                current_cost, current_idx = heapq.heappop(pq)

                if current_idx == goal_idx:
                    break

                for neighbor_idx in self._get_neighbors(current_idx):
                    if neighbor_idx < 0 or neighbor_idx >= len(self.map.nodes):
                        continue

                    new_cost = cost_so_far[current_idx] + self._euclidean_distance(
                        self.map.nodes[current_idx], self.map.nodes[neighbor_idx]
                    )

                    if neighbor_idx not in cost_so_far or new_cost < cost_so_far[neighbor_idx]:
                        cost_so_far[neighbor_idx] = new_cost
                        priority = new_cost + self._euclidean_distance(
                            self.map.nodes[neighbor_idx], self.map.nodes[goal_idx]
                        )
                        heapq.heappush(pq, (priority, neighbor_idx))
                        came_from[neighbor_idx] = current_idx

            # Reconstruct the path
            path = []
            current_idx = goal_idx
            while current_idx is not None:
                path.append(self.map.nodes[current_idx])
                current_idx = came_from.get(current_idx)

            path.reverse()

            #print(f"Sphero [{self.sphero_id}] found path: {path}")
            return path

        except Exception as e:
            print(f"Error finding path: {e}")
            return []

    def _get_neighbors(self, idx):
        """
        Retrieve neighbors of a node from the PRM structure.
        Args:
            idx: Index of the current node in the PRM nodes list.
        Returns:
            List of neighbor indices.
        """
        try:
            neighbors = []
            current_node = self.map.nodes[idx]
            for node1, node2 in self.map.edges:
                if node1 == current_node:
                    neighbor_idx = self.map.nodes.index(node2)
                    neighbors.append(neighbor_idx)
                elif node2 == current_node:
                    neighbor_idx = self.map.nodes.index(node1)
                    neighbors.append(neighbor_idx)
            return neighbors
        except Exception as e:
            print(f"Error getting neighbors: {e}")
            return []

    def submit_trajectory(self):
        """
        Submit the planned trajectory to the Planner's queue for collision evaluation.
        Args:
            planner: Reference to the Planner instance.
        """
        try:
            current_position = (self.current_y, self.current_x)
            trajectory = self._find_path(current_position)
            self.planner.add_trajectory((trajectory, self))
            #print(f"Sphero [{self.sphero_id}] submitted trajectory: {trajectory}")
        except Exception as e:
            print(f"Error submitting trajectory: {e}")

    @staticmethod
    def _euclidean_distance(p1, p2):
        """
        Calculate Euclidean distance between two points.
        Args:
            p1: First point as a tuple (x, y).
            p2: Second point as a tuple (x, y).
        Returns:
            Euclidean distance as a float.
        """
        try:
            return np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
        except Exception as e:
            print(f"Error calculating Euclidean distance: {e}")
            return float('inf')
