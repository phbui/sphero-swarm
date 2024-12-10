import math
from multiprocessing import Process
import math
import spherov2
from spherov2.utils import ToyUtil
from spherov2.helper import bound_color
from spherov2.types import Color

def new_set_matrix_line(self, x1: int, y1: int, x2: int, y2: int, color: Color):
    dx = abs()
    dy = abs(y2 - y1)
    if (dx != 0 and dy != 0 and dx != dy) or (dx == 0 and dy == 0):
        raise Exception("Can only draw straight lines and diagonals")

    line_length = max(abs(dx), abs(dy))
    for line_increment in range(line_length + 1):
        x_ = x1 + int((dx / line_length) * line_increment)
        y_ = y1 + int((dy / line_length) * line_increment)
        strMapLoc = f"{x_}:{y_}"
        self.__leds[strMapLoc] = bound_color(color, self.__leds[strMapLoc])

    ToyUtil.set_matrix_line(self.__toy, x1, y1, x2, y2, color.r, color.g, color.b, is_user_color=False)

# Monkey-patch the method
spherov2.OriginalClass.set_matrix_line = new_set_matrix_line

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

            self.droid.set_compass_direction(round(deg))

            self.droid.roll(0, 30, math.sqrt(deltax ** 2 + deltay ** 2) * self.multiplier)
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
            self.droid.set_compass_direction(angle)
            self.droid.roll(0, 30, duration)
        except Exception as e:
            print(f"Error in move_direction: {e}")

    def set_matrix(self, pattern):

        #The spher
        try:
            self.droid.clear_matrix()
            if pattern == "X":
                self.droid.set_compass_direction(0)
                if self.client_id == "SB-2E86" or self.client_id == "SB-D8B2":
                    self.droid.set_matrix_line(0,0,7,7,Color(r=255,g=0,b=0))
                    self.droid.set_matrix_line(1,0,7,6,Color(r=255, g=0, b=0))
                    self.droid.set_matrix_line(0,1,6,7,Color(r=255, g=0, b=0))
                elif self.client_id == "SB-4844" or self.client_id == "SB-7104":
                    self.droid.set_matrix_line(0,7,7,0,Color(r=255,g=0,b=0))
                    self.droid.set_matrix_line(0,6,6,0,Color(r=255, g=0, b=0))
                    self.droid.set_matrix_line(1,7,7,1,Color(r=255, g=0, b=0))
                else:
                    print("Droid not found")
            # Add more patterns as needed
        except Exception as e:
            print(f"Error in set_matrix: {e}")
