
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.utils import ToyUtil
from spherov2.helper import bound_color
from spherov2.types import Color

class MySpheroEduAPI(SpheroEduAPI):
    def set_matrix_line(self, x1: int, y1: int, x2: int, y2: int, color: Color):
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        if (dx != 0 and dy != 0 and dx != dy) or (dx == 0 and dy == 0):
            raise Exception("Can only draw straight lines and diagonals")

        line_length = max(dx, dy)

        # Since __leds and __toy are private attributes, use their mangled names.
        # In a subclass, Python still uses name mangling. The attribute `__leds` in SpheroEduAPI is stored as `_SpheroEduAPI__leds`.
        leds = self._SpheroEduAPI__leds
        toy = self._SpheroEduAPI__toy

        for line_increment in range(line_length + 1):
            x_ = x1 + int((dx / line_length) * line_increment)
            y_ = y1 + int((dy / line_length) * line_increment)
            strMapLoc = f"{x_}:{y_}"
            leds[strMapLoc] = bound_color(color, leds[strMapLoc])

        ToyUtil.set_matrix_line(toy, x1, y1, x2, y2, color.r, color.g, color.b, is_user_color=False)
