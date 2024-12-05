import math
from multiprocessing import Process
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
import time

class SpheroMovement:
    def __init__(self, toy, client_id, client_color, outgoing_queue):
        self.toy = toy
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
            with SpheroEduAPI(self.toy) as droid:
                droid.set_main_led(self.client_color)

                deltax = target[0] - current[0]
                deltay = target[1] - current[1]

                rad = math.atan2(-deltax, deltay)
                deg = rad * (180 / math.pi)
                if deg < 0:
                    deg += 360

                droid.roll(round(deg), 30, math.sqrt(deltax ** 2 + deltay ** 2) * self.multiplier)
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
            with SpheroEduAPI(self.toy) as droid:
                droid.set_main_led(self.client_color)
                droid.roll(angle, 30, duration)
        except Exception as e:
            print(f"Error in move_direction: {e}")

    def set_matrix(self, pattern):
        try:
            with SpheroEduAPI(self.toy) as droid:
                if pattern == "X":
                    droid.set_matrix_character("X", self.client_color)
                # Add more patterns as needed
        except Exception as e:
            print(f"Error in set_matrix: {e}")
