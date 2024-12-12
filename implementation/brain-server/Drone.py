import numpy as np
from scipy.spatial import KDTree
import heapq
import Localizer
import asyncio
import json

def send_message(ws, id, message_type, message_content):
    """
    Sends a message to the WebSocket server in a non-async way.
    Args:
        ws: WebSocket connection instance.
        id: Unique identifier for the message sender.
        message_type: Type of message (e.g., "BrainControl").
        message_content: Content of the message to be sent.
    """
    try:
        # Prepare the message
        message = {
            "clientType": "SpheroBrain",
            "id": id,
            "messageType": message_type,
            "message": message_content,
        }

        message = json.dumps(message)

        # Get the running event loop and run the async send_message coroutine in a thread-safe way
        loop = asyncio.get_running_loop()
        asyncio.run_coroutine_threadsafe(_send_message_async(ws, message), loop)
        print(f"WebSocket: Sent message: {message}")
    except Exception as e:
        print(f"WebSocket: Error sending message in `send_message`: {e}")

async def _send_message_async(ws, message):
    """
    Async function to send the message via the WebSocket connection.
    Args:
        ws: WebSocket connection instance.
        message: JSON-formatted message to send.
    """
    try:
        await ws.send(message)
    except Exception as e:
        print(f"WebSocket: Error sending message in `_send_message_async`: {e}")

class Drone:
    def __init__(self, camera, display, sphero_id, sphero_color, map):
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
            self.display = display
            self.sphero_id = sphero_id
            self.sphero_color = sphero_color
            print(f"Sphero Initialized: {sphero_id}")
            self.localizer = Localizer.Localizer(camera, display, sphero_color, 100)
            self.map = map
            self.goal = self._initialize_goal()
            self.prm_nodes = self.map.nodes  # Set PRM nodes from the map
            self.last_x = -1  # Last known x-coordinate of the drone
            self.last_y = -1  # Last known y-coordinate of the drone
            self.current_state_index = 0  # Start with "move_to_goal"
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
                "state": "reaching_goal",
                "description": "Sphero adjusts its position to precisely align with the goal.",
                "transitions": [
                    {
                        "condition": "Precisely aligned with the goal",
                        "next_state": "interact"
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
        except Exception as e:
            print(f"Error initializing Drone: {e}")

    def _initialize_goal(self):
        """
        Initialize the goal position based on the map's goal attribute.
        Returns:
            The goal as a tuple (x, y).
        """
        try:
            if len(self.map.goal) == 4:
                # If the goal is represented as a rectangle, use its center as the target goal
                x_min, y_min, x_max, y_max = self.map.goal
                return ((x_min + x_max) / 2, (y_min + y_max) / 2)
            else:
                # Assume goal is already a tuple (x, y)
                return self.map.goal
        except Exception as e:
            print(f"Error initializing goal: {e}")
            return None

    def get_position(self):
        """
        Get the current position of the Sphero using localization.
        Returns:
            Tuple (x, y) representing the current position.
        """
        try:
            return self.localizer.updateParticles()
        except Exception as e:
            print(f"Error in `get_position`: {e}")
            return None, None

    def move(self, target_x, target_y):
        """
        Move the Sphero to the target position.
        Args:
            target_x: Target x-coordinate.
            target_y: Target y-coordinate.
        Returns:
            Tuple (x, y) representing the new position.
        """
        try:
            print(f"Sphero [{self.sphero_id}] moving to x: {target_x}, y: {target_y}")
            # Placeholder for actual movement logic; update position directly
            self.last_x, self.last_y = target_x, target_y
            return target_x, target_y
        except Exception as e:
            print(f"Error in `move`: {e}")

    def execute_state(self, ws):
        """
        Execute the current state of the Sphero.
        Args:
            ws: WebSocket connection for sending updates.
        """
        try:
            current_state = self.states[self.current_state_index]
            state_name = current_state["state"]
            print(f"Sphero [{self.sphero_id}] executing state: {state_name}")

            if state_name == "move_to_goal":
                self._move_to_goal(ws)
            elif state_name == "reaching_goal":
                self._reaching_goal()
            elif state_name == "interact":
                self._interact()
        except Exception as e:
            print(f"Error in `execute_state`: {e}")

    def _move_to_goal(self, ws):
        """
        Navigate towards the goal and send movement updates.
        Args:
            ws: WebSocket connection for sending updates.
        """
        try:
            if not self.goal:
                print(f"Sphero [{self.sphero_id}]: Goal is not set!")
                return

            # Find the path to the goal
            current_location = self.get_position()
            print(f"{self.sphero_id} at {current_location}")
            path = self._find_path(current_location, self.goal)

            if path and len(path) > 1:
                # Move to the next point on the path
                next_point = path[1]
                print(f"{self.sphero_id} moving to {next_point}")
                current_x, current_y = self.get_position()
                if self._euclidean_distance((current_x, current_y), self.goal) <= 10:
                    self._transition_to_state("reaching_goal")
                else:
                    # Prepare the message content and send updates
                    message_content = {
                        "id": self.sphero_id,
                        "current_x": float(current_x),
                        "current_y": float(current_y),
                        "target_x": float(next_point[0]),
                        "target_y": float(next_point[1]),
                        "last_x": float(self.last_x),
                        "last_y": float(self.last_y)
                    }

                    self.move(next_point[0], next_point[1])
                    send_message(ws, self.sphero_id, "BrainControl", message_content)
        except Exception as e:
            print(f"Error in `_move_to_goal`: {e}")

    def _find_path(self, start, goal):
        """
        Find the shortest path from start to goal using the PRM nodes.
        Args:
            start: Starting position as a tuple (x, y).
            goal: Goal position as a tuple (x, y).
        Returns:
            List of tuples representing the path.
        """
        try:
            # Validate start and goal
            if start is None or goal is None:
                raise ValueError(f"Invalid start or goal: start={start}, goal={goal}")
            if not np.isfinite(start).all() or not np.isfinite(goal).all():
                raise ValueError(f"Non-finite values in start or goal: start={start}, goal={goal}")

            if not self.prm_nodes:
                print(f"Sphero [{self.sphero_id}] has no PRM nodes available!")
                return []

            # Use A* algorithm to find the shortest path on the PRM
            tree = KDTree(self.prm_nodes)
            start_idx = int(tree.query(start)[1])  # Convert to Python int
            goal_idx = int(tree.query(goal)[1])  # Convert to Python int
            return self._astar(start_idx, goal_idx)
        except Exception as e:
            print(f"Error in `_find_path`: {e}")
            return []

    def _astar(self, start_idx, goal_idx):
        """
        A* algorithm implementation for pathfinding.
        Args:
            start_idx: Index of the start node.
            goal_idx: Index of the goal node.
        Returns:
            Reconstructed path as a list of nodes.
        """
        try:
            pq = []
            heapq.heappush(pq, (0, start_idx))
            came_from = {start_idx: None}
            cost_so_far = {start_idx: 0}

            while pq:
                current_cost, current_idx = heapq.heappop(pq)

                if current_idx == goal_idx:
                    break

                neighbors = self._get_neighbors(current_idx)
                for neighbor_idx in neighbors:
                    new_cost = cost_so_far[current_idx] + self._euclidean_distance(
                        self.prm_nodes[current_idx], self.prm_nodes[neighbor_idx]
                    )
                    if neighbor_idx not in cost_so_far or new_cost < cost_so_far[neighbor_idx]:
                        cost_so_far[neighbor_idx] = new_cost
                        priority = new_cost + self._euclidean_distance(
                            self.prm_nodes[neighbor_idx], self.prm_nodes[goal_idx]
                        )
                        heapq.heappush(pq, (priority, neighbor_idx))
                        came_from[neighbor_idx] = current_idx

            return self._reconstruct_path(came_from, goal_idx)
        except Exception as e:
            print(f"Error in `_astar`: {e}")
            return []

    def _reconstruct_path(self, came_from, goal_idx):
        """
        Reconstruct the path from the goal to the start using the came_from dictionary.
        Args:
            came_from: Dictionary mapping each node to its predecessor.
            goal_idx: Index of the goal node.
        Returns:
            List of nodes representing the path.
        """
        try:
            path = []
            current_idx = goal_idx
            while current_idx is not None:
                path.append(self.prm_nodes[current_idx])
                current_idx = came_from[current_idx]
            path.reverse()
            return path
        except Exception as e:
            print(f"Error in `_reconstruct_path`: {e}")
            return []
