import math
from multiprocessing import Process


class SpheroMovement:
    def __init__(self, droid, client_id, client_color, outgoing_queue):
        self.droid = droid  # Use the persistent SpheroEduAPI instance
        self.client_id = client_id
        self.client_color = client_color
        self.outgoing_queue = outgoing_queue
        self.multiplier = 0.3  # Timing adjustment for movements

    def send_feedback(self, message):
        try:
            message_json = {
                "clientType": "SpheroController",
                "id": self.client_id,
                "messageType": "SpheroFeedback",
                "message": message
            }
            process = Process(target=self.outgoing_queue.put, args=(message_json,))
            process.start()
            process.join()
        except Exception as e:
            print(f"Error sending feedback: {e}")

    def move(self, current, target):
        try:
            self.droid.set_main_led(self.client_color)  # Use the persistent droid instance

            deltax = target[0] - current[0]
            deltay = target[1] - current[1]

            rad = math.atan2(-deltax, deltay)
            deg = rad * (180 / math.pi)
            if deg < 0:
                deg += 360

            self.droid.roll(round(deg), 30, math.sqrt(deltax ** 2 + deltay ** 2) * self.multiplier)
        except Exception as e:
            print(f"Error in move: {e}")
        self.send_feedback("Done")

    def move_direction(self, direction, duration):
        directions = {
            "north": 0,
            "east": 90,
            "south": 180,
            "west": 270
        }
        angle = directions.get(direction.lower(), 0)

        try:
            self.droid.set_main_led(self.client_color)
            self.droid.roll(angle, 30, duration)
        except Exception as e:
            print(f"Error in move_direction: {e}")

    def set_matrix(self, pattern):
        try:
            if pattern == "X":
                self.droid.set_matrix_character("X", self.client_color)
            # Add more patterns as needed
        except Exception as e:
            print(f"Error in set_matrix: {e}")
