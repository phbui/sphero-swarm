from spherov2.sphero_edu import SpheroEduAPI
from spherov2.utils import ToyUtil
from spherov2.helper import bound_color
from spherov2.types import Color

class MySpheroEduAPI(SpheroEduAPI):
    """
    Subclass of SpheroEduAPI to fix a broken function for drawing lines on the Sphero matrix.
    """
    def set_matrix_line(self, x1: int, y1: int, x2: int, y2: int, color: Color):
        """
        Draw a line or diagonal on the Sphero LED matrix.

        Args:
            x1 (int): Starting x-coordinate of the line.
            y1 (int): Starting y-coordinate of the line.
            x2 (int): Ending x-coordinate of the line.
            y2 (int): Ending y-coordinate of the line.
            color (Color): Color of the line.

        Raises:
            Exception: If the line is not straight (horizontal, vertical) or diagonal.
        """
        # Calculate the differences in x and y coordinates
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)

        # Validate that the line is either straight or diagonal
        if (dx != 0 and dy != 0 and dx != dy) or (dx == 0 and dy == 0):
            raise Exception("Can only draw straight lines and diagonals")

        line_length = max(dx, dy)  # Determine the length of the line

        # Access private attributes __leds and __toy using name mangling
        leds = self._SpheroEduAPI__leds
        toy = self._SpheroEduAPI__toy

        # Iterate through each point on the line
        for line_increment in range(line_length + 1):
            x_ = x1 + int((dx / line_length) * line_increment)  # Calculate the x-coordinate
            y_ = y1 + int((dy / line_length) * line_increment)  # Calculate the y-coordinate
            strMapLoc = f"{x_}:{y_}"  # Create the LED map location key

            # Update the LED matrix with the new color, ensuring it is within bounds
            leds[strMapLoc] = bound_color(color, leds[strMapLoc])

        # Use ToyUtil to send the line drawing command to the Sphero device
        ToyUtil.set_matrix_line(toy, x1, y1, x2, y2, color.r, color.g, color.b, is_user_color=False)
