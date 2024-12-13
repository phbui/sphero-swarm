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
            self.current_confidence = 0

            self.last_attempt = None  # Store the last visited point
            self.last_location = None

            # Kalman filter
            self.angle = -1
            self.speed = -1

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

    def calculate_movement_parameters(self, target_position):
        """
        Calculate the angle and timing needed to reach the target position with Kalman-like correction.

        Args:
            target_position: Tuple (y, x) representing the target position.

        Returns:
            tuple: (corrected_angle, timing)
        """
        try:
            # Handle uninitialized state
            if self.last_location is None:
                self.last_location = (self.current_y, self.current_x)
                self.last_attempt = target_position
                return 0, 2  # Initial angle and default timing

            if self.angle == -1 or self.speed == -1:
                # Second move: Initialize angle and speed using observed values
                delta_y_actual = self.current_y - self.last_location[0]
                delta_x_actual = self.current_x - self.last_location[1]

                observed_angle = math.degrees(math.atan2(delta_x_actual, delta_y_actual)) % 360
                distance_traveled = math.sqrt(delta_x_actual**2 + delta_y_actual**2)
                observed_speed = distance_traveled / 2  # Assume default timing of 2 seconds

                # Initialize states
                self.angle = observed_angle
                self.speed = observed_speed

                # Update last positions
                self.last_location = (self.current_y, self.current_x)
                self.last_attempt = target_position

                return self.angle, 2  # Return observed angle and default timing

            # Previous positions: a (start), b (intended target), c (current actual position)
            a = self.last_location
            b = self.last_attempt
            c = (self.current_y, self.current_x)
            confidence = self.current_confidence

            # Calculate angle a -> b (previous intended direction)
            delta_y_intended = b[0] - a[0]
            delta_x_intended = b[1] - a[1]
            angle_intended = math.degrees(math.atan2(delta_x_intended, delta_y_intended))

            # Calculate angle a -> c (actual movement direction)
            delta_y_actual = c[0] - a[0]
            delta_x_actual = c[1] - a[1]
            angle_actual = math.degrees(math.atan2(delta_x_actual, delta_y_actual))

            # Correct the previous angle (z): angle_actual - angle_intended + previous_angle
            correction_angle = angle_actual - angle_intended
            observed_angle = (self.angle + correction_angle) % 360

            adjusted_angle_weight = confidence
            adjusted_speed_weight = confidence

            # Apply Kalman-like correction for angle
            self.angle = (
                adjusted_angle_weight * self.angle + (1 - adjusted_angle_weight) * observed_angle
            ) % 360

            # Calculate the current angle to the target (c -> target)
            delta_y_target = target_position[0] - c[0]
            delta_x_target = target_position[1] - c[1]
            target_angle = math.degrees(math.atan2(delta_x_target, delta_y_target))

            # Combine corrected angle with current target angle
            corrected_angle = (self.angle + target_angle) % 360

            # Calculate observed speed from the previous movement
            distance_traveled = math.sqrt(delta_x_actual**2 + delta_y_actual**2)
            observed_speed = distance_traveled / 2  # Assume previous timing of 2 seconds

            # Apply Kalman-like correction for speed
            self.speed = adjusted_speed_weight * self.speed + (1 - adjusted_speed_weight) * observed_speed

            # Calculate distance to target
            distance_to_target = math.sqrt(delta_x_target**2 + delta_y_target**2)

            # Calculate timing based on corrected speed
            timing = distance_to_target / (self.speed + 1e-6)  # Avoid division by zero

            # Update state
            self.last_location = (self.current_y, self.current_x)
            self.last_attempt = target_position

            return corrected_angle, timing

        except ZeroDivisionError:
            print("Error: Division by zero occurred in timing calculation.")
            return self.angle, 2  # Fallback timing

        except ValueError as ve:
            print(f"Error: Value error occurred - {ve}")
            return self.angle, 2  # Fallback timing

        except Exception as e:
            print(f"Unexpected error in calculate_movement_parameters: {e}")
            return self.angle, 2  # Fallback timing
        
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
            # Draw a point at the target position
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
                print(f"Sphero [{self.sphero_id}]: Goal is not set!")
                return
            
            print(f"Sphero [{self.sphero_id}] at: y:{self.current_y}, x:{self.current_x}")

            

            if (self.reached_goal()):
                self._transition_to_state("interact")
            else:
                self.submit_trajectory()

        except Exception as e:
            print(f"Error in _move_to_goal: {e}")

    def reached_goal(self, ):
        """
        Fine-tune the Sphero's position to align with the goal.
        """
        try:
            if self._euclidean_distance((self.current_x, self.current_y), self.goal) <= 5:
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

            print(f"Sphero [{self.sphero_id}] found path: {path}")
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
            print(f"Sphero [{self.sphero_id}] submitted trajectory: {trajectory}")
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

