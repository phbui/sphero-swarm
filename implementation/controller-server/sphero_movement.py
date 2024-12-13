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
            self.droid.roll(0, 30, duration)  # Move the Sphero
        except Exception as e:
            print(f"Error in move_direction: {e}")

    def set_matrix(self, pattern):
        """
        Set the LED matrix to display a specific pattern.

        Args:
            pattern: Pattern to display (e.g., "X").
        """
        try:
            self.droid.clear_matrix()  # Clear the existing LED matrix

            if pattern == "X":
                self.droid.set_compass_direction(0)  # Reset compass direction

                # Define patterns for specific Spheros
                if self.sphero_id == "SB-2E86" or self.sphero_id == "SB-D8B2":
                    self.droid.set_matrix_line(0, 0, 7, 7, Color(r=255, g=0, b=0))
                    self.droid.set_matrix_line(1, 0, 7, 6, Color(r=255, g=0, b=0))
                    self.droid.set_matrix_line(0, 1, 6, 7, Color(r=255, g=0, b=0))
                elif self.sphero_id == "SB-4844" or self.sphero_id == "SB-7104":
                    self.droid.set_matrix_line(0, 7, 7, 0, Color(r=255, g=0, b=0))
                    self.droid.set_matrix_line(0, 6, 6, 0, Color(r=255, g=0, b=0))
                    self.droid.set_matrix_line(1, 7, 7, 1, Color(r=255, g=0, b=0))
                elif self.sphero_id == "SB-E12C":
                    self.droid.set_matrix_line(0, 0, 7, 7, Color(r=255, g=0, b=0))
                    self.droid.set_matrix_line(1, 0, 7, 6, Color(r=255, g=0, b=0))
                    self.droid.set_matrix_line(0, 1, 6, 7, Color(r=255, g=0, b=0))
                    self.droid.set_matrix_line(0, 7, 7, 0, Color(r=255, g=0, b=0))
                    self.droid.set_matrix_line(0, 6, 6, 0, Color(r=255, g=0, b=0))
                    self.droid.set_matrix_line(1, 7, 7, 1, Color(r=255, g=0, b=0))
                else:
                    print("Droid not found")
        except Exception as e:
            print(f"Error in set_matrix: {e}")
