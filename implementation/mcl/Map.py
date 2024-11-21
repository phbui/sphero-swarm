import os
import cv2

SCALE_FACTOR = 50  # 1 unit of distance = 50 pixels

class Map:
    def __init__(self, folder="./maps/"):
        self.folder = folder
        self.maps = [f for f in os.listdir(self.folder) if f.endswith(('.png', '.jpg'))]
        self.image = None
        self.width = 0
        self.height = 0
        self.x_min = 0
        self.x_max = 0
        self.y_min = 0
        self.y_max = 0

    def select_map(self):
        print("Available map images:")
        for i, filename in enumerate(self.maps):
            print(f"{i + 1}. {filename}")

        while True:
            try:
                choice = int(input(f"Select a picture by number (1 - {len(self.maps)}): ")) - 1
                if 0 <= choice < len(self.maps):
                    map_obj = self.maps[choice]
                    break
                else:
                    print(f"Please select a number between 1 and {len(self.maps)}.")
            except ValueError:
                print("Invalid input. Please enter a number.")

        self.image = cv2.imread(os.path.join(self.folder, map_obj))
        self.height, self.width, _ = self.image.shape
        print(f"Selected Map: {map_obj}")

        self.x_min = -self.width / (2 * SCALE_FACTOR)
        self.x_max = self.width / (2 * SCALE_FACTOR)
        self.y_min = -self.height / (2 * SCALE_FACTOR)
        self.y_max = self.height / (2 * SCALE_FACTOR)

    def map_to_pixel(self, x, y):
        pixel_x = int((x * SCALE_FACTOR) + (self.width / 2))
        pixel_y = int((-y * SCALE_FACTOR) + (self.height / 2))
        return pixel_x, pixel_y

    def pixel_to_map(self, pixel_x, pixel_y):
        # Convert pixel coordinates back to map (world) coordinates
        x = (pixel_x - (self.width / 2)) / SCALE_FACTOR
        y = -((pixel_y - (self.height / 2)) / SCALE_FACTOR)
        return x, y
