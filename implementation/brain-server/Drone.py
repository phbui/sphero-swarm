import numpy as np
import heapq
import Localizer
import math
import time

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

            self.last_attempt = None
            self.last_location = None

            # Movement parameters
            self.angle = 0
            self.speed = None
            self.timing = 2
            self.angle_offset = None
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
            self.current_state_index = 0
        except Exception as e:
           print(f"Error initializing Drone: {e}")

    def calculate_movement_parameters(self, target_position):
        """
        Calculate the angle, speed, and timing needed to reach the target position with feedback correction.

        Args:
            target_position: Tuple (y, x) representing the target position.

        Returns:
            tuple: (corrected_angle, corrected_speed, corrected_timing)
        """
        try:
            # If this is the first move
            if self.last_location is None:
                #print("[Movement Parameters] First Move: Setting True North.")
                self.last_location = (self.current_y, self.current_x)
                return self.angle, self.timing

            # Calculate actual movement vector
            delta_x_actual = self.current_x - self.last_location[1]
            delta_y_actual = self.current_y - self.last_location[0]

            actual_angle = math.degrees(math.atan2(delta_x_actual, -delta_y_actual)) % 360
            distance_moved = math.sqrt(delta_x_actual**2 + delta_y_actual**2)

            if self.angle_offset is None:
                self.angle_offset = actual_angle

            # Update speed based on current confidence
            updated_speed = (distance_moved / self.timing)
            if self.speed is not None:
                updated_speed = (1 - self.current_confidence) * self.speed + self.current_confidence * updated_speed
            self.speed = updated_speed

            # Calculate angle to the new target
            delta_x_target = target_position[1] - self.current_x
            delta_y_target = target_position[0] - self.current_y
            target_angle = (math.degrees(math.atan2(delta_x_target, -delta_y_target)) - self.angle_offset) % 360

            # Calculate corrected timing
            distance_to_target = math.sqrt(delta_x_target**2 + delta_y_target**2)
            corrected_timing = distance_to_target / (self.speed + 1e-6)

            end_x = self.current_x + 100 * math.cos(math.radians(self.angle_offset))
            end_y = self.current_y - 100 * math.sin(math.radians(self.angle_offset)) 

            # Draw the predicted angle direction
            self.display.draw_line(
                id=f"{self.sphero_id}_offset_angle",
                point1=(self.current_y, self.current_x),
                point2=(end_y, end_x),
                weight=2,
                color='#00FF00'  
            )


            end_x = self.current_x + 100 * math.cos(math.radians(0))
            end_y = self.current_y - 100 * math.sin(math.radians(0)) 

            self.display.draw_line(
                id=f"{self.sphero_id}_zero_angle",
                point1=(self.current_y, self.current_x),
                point2=(end_y, end_x),
                weight=2,
                color='#FF0000'  
            )


            # Update state
            self.angle = target_angle
            self.last_attempt = target_position
            self.last_location = (self.current_y, self.current_x)
            self.timing = corrected_timing

            #print("[Movement Parameters] Calculated Values:")
            return self.angle, self.timing
        except ZeroDivisionError:
            print("[Movement Parameters] Division by zero in timing calculation.")
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
            self.submit_trajectory()
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
            if self.reached_goal():
                return[(self.current_y,self.current_x), (self.current_y,self.current_x)]
            

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
            #print(f"Closest Node to Start: y:{closest_node[1]}, x: {closest_node[0]}")
            #print(f"Closest Node to Goal: y:{goal_node[1]}, x: {goal_node[0]}")

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
            trajectory = (self._find_path(current_position))[:2]
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
