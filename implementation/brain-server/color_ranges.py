import numpy as np

color_ranges = {
    '#FF00FF': ([120, 0, 230], [150, 255, 255]),  # Pink
    '#FF0000': ([30, 60, 175], [180, 255, 255]),  # Red
    '#035900': ([80, 115, 65], [95, 255, 255]),  # Green
    '#020082': ([70, 20, 180], [180, 100, 255]),  # Blue
    '#FFFF00': ([50, 0, 245], [80, 80, 255])   # Yellow
}

obstacle_range = {
    "lower": np.array([5, 135, 60]),
    "upper": np.array([20, 255, 240])
}
goal_range = {
    "lower": np.array([125, 115, 100]),
    "upper": np.array([130, 140, 130])
}