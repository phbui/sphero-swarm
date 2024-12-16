from multiprocessing import Process
from spherov2.types import Color

class SpheroMovement:
    def __init__(self, droid, sphero_id, sphero_color, outgoing_queue):
        """
        Initialize the SpheroMovement class to manage Sphero movements and feedback.

        Args:
            droid: Persistent SpheroEduAPI instance to control the Sphero.
            sphero_id: Unique identifier for the Sphero client.
            sphero_color: Color for the Sphero's main LED.
            outgoing_queue: Queue for sending feedback messages.
        """
        self.droid = droid
        self.sphero_id = sphero_id
        self.sphero_color = sphero_color
        self.outgoing_queue = outgoing_queue

    def send_feedback(self, message):
        """
        Send feedback messages to the outgoing queue.

        Args:
            message: Feedback message to send.
        """
        try:
            message_json = {
                "clientType": "SpheroController",
                "id": self.sphero_id,
                "messageType": "SpheroFeedback",
                "message": message
            }
            process = Process(target=self.outgoing_queue.put, args=(message_json,))
            process.start()
            process.join()
        except Exception as e:
            print(f"Error sending feedback: {e}")

    def move(self, angle, timing):
        """
        Move the Sphero from the current position to the target position.

        Args:
            current: Tuple (x, y) representing the current position.
            target: Tuple (x, y) representing the target position.
        """
        try:
            self.droid.set_main_led(self.sphero_color)  # Set the main LED to the client color

            self.droid.set_compass_direction(round(angle))

            # Use the provided timing for movement
            self.set_matrix(pattern="X")
            self.droid.roll(angle, 20, timing)
            print(f"[{self.sphero_id}] Movement complete.")
            self.send_feedback(self.sphero_id)
        except Exception as e:
            print(f"Error in move: {e}")



    def move_direction(self, direction, duration):
        """
        Move the Sphero in a specific direction for a given duration.

        Args:
            direction: Cardinal direction as a string ("north", "east", "south", "west").
            duration: Duration of the movement in seconds.
        """
        directions = {
            "north": 0,
            "east": 90,
            "south": 180,
            "west": 270
        }
        angle = directions.get(direction.lower(), 0)  # Default to 0 degrees if direction is invalid

        try:
            self.droid.set_main_led(self.sphero_color)  # Set the main LED to the client color
            self.droid.set_compass_direction(angle)  # Set the compass direction
            self.droid.roll(0, 40, duration)  # Move the Sphero
        except Exception as e:
            print(f"Error in move_direction: {e}")

    def set_matrix(self, pattern="X"):
        """
        Set the LED matrix to display a specific pattern.

        Args:
            pattern: Pattern to display (e.g., "X").
        """
        try:
            self.droid.clear_matrix()  # Clear the existing LED matrix

            if pattern == "X":
                self.droid.set_compass_direction(0)  # Reset compass direction
                arrow_color = Color(255, 0, 0)  # Red color

                # Draw the stem of the arrow
                self.droid.set_matrix_line(4, 2, 4, 5, arrow_color)

                # Draw the left diagonal head
                self.droid.set_matrix_line(3, 1, 4, 2, arrow_color)

                # Draw the right diagonal head
                self.droid.set_matrix_line(4, 2, 5, 1, arrow_color)
        except Exception as e:
            print(f"Error in set_matrix: {e}")
