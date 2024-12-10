import numpy as np
from scipy.spatial import KDTree
import heapq
import Localizer
import asyncio
import json

def send_message(ws, id, message_type, message_content):
    """Sends a message to the WebSocket server in a non-async way."""
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
        print(f"WebSocket: Error sending message: {e}")

async def _send_message_async(ws, message):
    """Async function to send the message via the WebSocket connection."""
    try:
        await ws.send( message)
    except Exception as e:
        print(f"WebSocket: Error sending message: {e}")

class Drone:
    def __init__(self, camera, display, sphero_id, sphero_color, map):
        """
        Initialize a Drone (Sphero) with its display, ID, and color.
        Args:
            display: The display instance for visualization.
            sphero_id: Unique identifier for the Sphero.
            sphero_color: Color used for identifying the Sphero.
            map: Reference to the Map instance.
        """
        self.display = display
        self.sphero_id = sphero_id
        self.sphero_color = sphero_color
        print(f"Sphero Initialized: {sphero_id}")
        self.localizer = Localizer.Localizer(camera, display, sphero_color, 100)
        self.map = map
        if len(self.map.goal) == 4:
            # map.goal = (x_min, y_min, x_max, y_max)
            x_min, y_min, x_max, y_max = self.map.goal
            goal_x = (x_min + x_max) / 2
            goal_y = (y_min + y_max) / 2
            self.goal = (goal_x, goal_y)
        else:
            # Assume goal is already a tuple (x, y)
            self.goal = self.map.goal
        self.prm_nodes = self.map.nodes  # Set PRM nodes from the map
        self.last_x = -1
        self.last_y = -1
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
        self.current_state_index = 0  # Start with "move_to_goal"

    def get_position(self):
        """
        Get the current position of the Sphero using localization.
        Returns:
            Tuple (x, y) representing the current position.
        """
        return self.localizer.updateParticles()

    def move(self, target_x, target_y):
        """
        Move the Sphero to the target position.
        Args:
            target_x: Target x-coordinate.
            target_y: Target y-coordinate.
        Returns:
            Tuple (x, y) representing the new position.
        """
        print(f"Sphero [{self.sphero_id}] moving to x: {target_x}, y: {target_y}")
        # Placeholder for actual movement logic; update position directly
        self.last_x = target_x
        self.last_y = target_y
        return target_x, target_y

    def execute_state(self, ws):
        """
        Execute the current state of the Sphero.
        Args:
            ws: WebSocket connection for sending updates.
        """
        current_state = self.states[self.current_state_index]
        state_name = current_state["state"]
        print(f"Sphero [{self.sphero_id}] executing state: {state_name}")

        if state_name == "move_to_goal":
            self._move_to_goal(ws)
        elif state_name == "reaching_goal":
            self._reaching_goal()
        elif state_name == "interact":
            self._interact()

    def _move_to_goal(self, ws):
        """
        Navigate towards the goal and send movement updates.
        Args:
            ws: WebSocket connection for sending updates.
        """
        if not self.goal:
            print(f"Sphero [{self.sphero_id}]: Goal is not set!")
            return

        path = self._find_path(self.get_position(), self.goal)

        if path and len(path) > 1:
            # Move to the next point on the path
            next_point = path[1]

            current_x, current_y = self.get_position()
            if self._euclidean_distance((current_x, current_y), self.goal) <= 10:
                self._transition_to_state("reaching_goal")
            else:
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


    def _reaching_goal(self):
        """
        Fine-tune the Sphero's position to align with the goal.
        """
        current_x, current_y = self.get_position()
        if self._euclidean_distance((current_x, current_y), self.goal) <= 5:
            print(f"Sphero [{self.sphero_id}] precisely aligned with the goal.")
            self._transition_to_state("interact")

    def _interact(self):
        """
        Execute interaction behavior.
        """
        print(f"Sphero [{self.sphero_id}] interacting.")
        # Add specific interaction logic here
        print(f"Sphero [{self.sphero_id}] interaction complete.")

    def _transition_to_state(self, next_state_name):
        """
        Transition to the specified state.
        Args:
            next_state_name: Name of the state to transition to.
        """
        for i, state in enumerate(self.states):
            if state["state"] == next_state_name:
                self.current_state_index = i
                print(f"Sphero [{self.sphero_id}] transitioning to state: {next_state_name}")
                return

    def _find_path(self, start, goal):
        """
        Find the shortest path from start to goal using the PRM nodes.
        Args:
            start: Starting position as a tuple (x, y).
            goal: Goal position as a tuple (x, y).
        Returns:
            List of tuples representing the path.
        """
        if not self.prm_nodes:
            print(f"Sphero [{self.sphero_id}] has no PRM nodes available!")
            return []

        # Use A* algorithm to find the shortest path on the PRM
        tree = KDTree(self.prm_nodes)
        start_idx = tree.query(start)[1]
        goal_idx = tree.query(goal)[1]

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

        # Reconstruct the path
        path = []
        current_idx = goal_idx
        while current_idx is not None:
            path.append(self.prm_nodes[current_idx])
            current_idx = came_from[current_idx]
        path.reverse()
        return path

    def _get_neighbors(self, idx):
        """
        Retrieve neighbors of a node from the PRM structure.
        Args:
            idx: Index of the current node in the PRM nodes list.
        Returns:
            List of neighbor indices.
        """
        neighbors = []
        current_node = self.prm_nodes[idx]
        for (node1, node2) in self.map.edges:
            if current_node == node1:
                neighbors.append(self.prm_nodes.index(node2))
            elif current_node == node2:
                neighbors.append(self.prm_nodes.index(node1))
        return neighbors

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
        return np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
