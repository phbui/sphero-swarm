import threading
import Camera
import Display
import Drone
import Map
import queue
import numpy as np
import asyncio
import json
import math

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
        message = {
            "clientType": "SpheroBrain",
            "id": id,
            "messageType": message_type,
            "message": message_content,
        }
        message = json.dumps(message)

        asyncio.run(_send_message_async(ws, message))
        #print(f"WebSocket: Sent message: {message}")
    except Exception as e:
        print(f"WebSocket: Error sending message: {e}")

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
        print(f"WebSocket: Error sending message: {e}")


class Planner:
    def __init__(self, spheros):
        """
        Initialize the Planner class to manage the overall system.
        Args:
            spheros: List of dictionaries, where each dictionary contains the "id" and "color" of a Sphero.
        """
        self.ws = None
        self.display = Display.Display()  # Initialize the display instance
        self.camera = Camera.Camera(self.display)  # Initialize the camera instance with the display
        self.camera.capture_image()  # Capture an initial image from the camera

        # Start a separate thread for continuously showing the display
        self.display_thread = threading.Thread(target=self.display.show, daemon=True)
        self.display_thread.start()

        # Initialize the map and generate the probabilistic roadmap (PRM)
        self.map = Map.Map(self.display)
        self.map.generate_prm()

        # Initialize the list of Spheros (Drones)
        self.spheros = [
            Drone.Drone(self, self.camera, self.display, sphero["id"], sphero["color"], self.map)
            for sphero in spheros
        ]

        self.trajectory_queue = queue.Queue()
        self.queue_condition = threading.Condition()  # Create a condition variable

    def start(self, ws):
        """
        Start the system by iterating over all Spheros and triggering their next moves.
        Args:
            ws: WebSocket connection to send updates.
        """
        print("System started.")
        threading.Thread(target=self.process_trajectories, daemon=True).start()
        self.ws = ws
        for sphero in self.spheros:
            sphero.execute_state()  # Trigger the state execution for each Sphero

    def _start_event_loop(self):
        """
        Start an asyncio event loop in the current thread.
        """
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        loop.run_forever()

    def next_move(self, id):
        """
        Trigger the next move for a specific Sphero based on its ID.
        Args:
            id: The unique ID of the Sphero to control.
        """
        for sphero in self.spheros:
            if sphero.sphero_id == id:  # Match the Sphero by ID
                sphero.execute_state()  # Trigger its state execution

    def add_trajectory(self, trajectory):
        """Add a trajectory to the queue and process if the queue is full."""
        with self.queue_condition:
            self.trajectory_queue.put(trajectory)
            if self.trajectory_queue.qsize() == len(self.spheros):
                # Notify all threads to process the trajectories
                self.queue_condition.notify_all()


    def process_trajectories(self):
        """Continuously process the trajectories in the queue, evaluate CVaR risk, and move drones."""
        while True:  # Run indefinitely to handle new trajectories as they come
            with self.queue_condition:
                while self.trajectory_queue.qsize() < len(self.spheros):
                    # Wait until all trajectories are in the queue
                    self.queue_condition.wait()

                #print("Analyzing trajectories")

                # Collect all trajectories from the queue
                trajectories = []
                while not self.trajectory_queue.empty():
                    trajectories.append(self.trajectory_queue.get())

                # Evaluate CVaR risk for collision
                collision_pairs = self._evaluate_collision_risk(trajectories)
                collision_ids = set()

                # Handle drones with potential collision risks
                for drone1, drone2 in collision_pairs:
                    print(f"Collision risk detected between Drone {drone1.sphero_id} and Drone {drone2.sphero_id}")
                    collision_ids.add(drone1.sphero_id)
                    collision_ids.add(drone2.sphero_id)
                    self._adjust_paths(drone1, drone2)

                # Handle drones with no collision risks
                for trajectory, drone in trajectories:
                    if drone.sphero_id not in collision_ids:
                        print(f"No collision detected for Drone {drone.sphero_id}. Moving to next point.")
                        if len(trajectory) > 1:
                            self._notify_and_move_drone(drone, trajectory[1])
                        else:
                            print(f"Drone {drone.sphero_id} has reached its final destination.")

                # Print completion message
                #print("All trajectories processed. Queue cleared.")

    def _evaluate_collision_risk(self, trajectories):
        """
        Evaluate risk for collisions among the given trajectories.
        Args:
            trajectories: List of trajectories submitted by drones.
        Returns:
            List of tuples representing pairs of drones at risk of collision.
        """
        collision_pairs = []
        for i in range(len(trajectories)):
            for j in range(i + 1, len(trajectories)):
                traj1, drone1 = trajectories[i]
                traj2, drone2 = trajectories[j]
                
                # Compute pairwise risk (using a simplified distance threshold for this example)
                risk = self._calculate_collision_risk(traj1, traj2)
                if False: #ignore this
                    collision_pairs.append((drone1, drone2))

        return collision_pairs

    def _calculate_collision_risk(self, traj1, traj2):
        """
        Calculate collision risk between two trajectories.
        """
        try:
            # min_distance = np.min([
            #     np.linalg.norm(np.array(p1) - np.array(p2))
            #     for p1 in traj1 for p2 in traj2
            # ])
            # risk = np.exp(-min_distance)  # Exponential decay of risk with distance
            return 0
        except Exception as e:
            print(f"Error calculating collision risk: {e}")
            return 0

    def _adjust_paths(self, drone1, drone2):
        """
        Adjust the paths of two drones to mitigate collision risk using PRM and dynamic path adjustments.
        Args:
            drone1: First drone involved in the collision risk.
            drone2: Second drone involved in the collision risk.
        """
        try:
            print(f"Adjusting paths for {drone1.sphero_id} & {drone2.sphero_id}")


            # Re-plan paths using PRM nodes
            new_path1 = drone1._find_path((drone1.current_y, drone1.current_x))
            new_path2 = drone2._find_path((drone2.current_y, drone2.current_x))

            # Check if paths have potential collision points
            collision_nodes = self._find_collision_nodes(new_path1, new_path2)

            if collision_nodes:
                print(f"Collision detected on nodes: {collision_nodes}")
                # Adjust paths to avoid collision nodes
                adjusted_path1 = self._reroute_path(drone1, new_path1, collision_nodes)
                adjusted_path2 = self._reroute_path(drone1, new_path2, collision_nodes)

                print(adjusted_path1)
                print(adjusted_path2)

                # Update paths and notify drones
                if len(adjusted_path1) > 1:
                    self._notify_and_move_drone(drone1, adjusted_path1[1])
                else:
                    print(f"Drone {drone1.sphero_id} has no valid adjusted path.")

                if len(adjusted_path2) > 1:
                    self._notify_and_move_drone(drone2, adjusted_path2[1])
                else:
                    print(f"Drone {drone2.sphero_id} has no valid adjusted path.")
            else:
                # If no collision detected, proceed with original paths
                if len(new_path1) > 1:
                    print(new_path1)
                    self._notify_and_move_drone(drone1, new_path1[1])
                else:
                    print(f"Drone {drone1.sphero_id} has no valid path adjustments.")

                if len(new_path2) > 1:
                    print(new_path2)
                    self._notify_and_move_drone(drone2, new_path2[1])
                else:
                    print(f"Drone {drone2.sphero_id} has no valid path adjustments.")

        except Exception as e:
            print(f"Error adjusting paths: {e}")

    def _find_collision_nodes(self, path1, path2):
        """
        Find collision points between two paths based on shared PRM nodes.
        Args:
            path1: Path of the first drone as a list of PRM nodes.
            path2: Path of the second drone as a list of PRM nodes.
        Returns:
            A set of nodes that are shared between the two paths (potential collision points).
        """
        return set(path1).intersection(path2)

    def _reroute_path(self, drone, path, collision_nodes):
        """
        Reroute a path to avoid specified collision nodes using the PRM.
        Args:
            path: Original path as a list of PRM nodes.
            collision_nodes: Set of nodes to avoid.
        Returns:
            Adjusted path that avoids collision nodes, if possible.
        """
        adjusted_path = []
        for node in path:
            if node not in collision_nodes:
                adjusted_path.append(node)
            else:
                # Attempt to find an alternate neighboring node
                neighbors = drone._get_neighbors(self.map.nodes.index(node))
                for neighbor in neighbors:
                    if neighbor not in collision_nodes and neighbor not in adjusted_path:
                        adjusted_path.append(neighbor)
                        break
        return adjusted_path

    def _notify_and_move_drone(self, drone, target_point):
        """
        Notify a drone of its updated path and move it to the next target point.
        Args:
            drone: The drone to notify and move.
            target_point: The next target point as a tuple (x, y).
        """
        try:
            print(f"curr: {drone.current_y}, {drone.current_x} | tar: {target_point}")
            current_y = drone.current_y 
            current_x = drone.current_x 
            target_x, target_y  = target_point
            angle_deg, timing = drone.calculate_movement_parameters((target_y, target_x))

            print(f"Corrected Angle: {angle_deg}, Timing: {timing}")
            print(f"Moving [{drone.sphero_id}] from Y: {current_y}, X: {current_x} to Y:{target_y}, X: {target_x}")

            message_content = {
                "id": drone.sphero_id,
                "angle": int(round(angle_deg)),
                "timing": float(timing)
            }

            drone.move(current_x, current_y, target_x, target_y)
            send_message(self.ws, drone.sphero_id, "BrainControl", message_content)
        except Exception as e:
            print(f"Error notifying and moving Drone {drone.sphero_id}: {e}")

