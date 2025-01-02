import numpy as np

color_ranges = {
    '#FF00FF': ([120, 0, 230], [150, 255, 255]),  # Pink
    '#FF0000': ([150, 30, 200], [180, 135, 255]),  # Red
    '#035900': ([80, 115, 65], [95, 255, 255]),  # Green
    '#020082': ([90, 75, 150], [110, 255, 255]),  # Blue
    '#FFFF00': ([0, 0, 225], [105, 25, 255]),  # Yello
}

obstacle_range = {
    "lower": np.array([5, 135, 60]),
    "upper": np.array([20, 255, 240])
}
goal_range = {
    "lower": np.array([115, 85, 30]),
    "upper": np.array([145, 255, 120])
}