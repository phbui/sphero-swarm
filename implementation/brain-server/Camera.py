import cv2
import time

SCALE_FACTOR = 50  # 1 unit of distance = 50 pixels

class Camera:
    def __init__(self, camera_index=0):
        """
        Initialize the Camera class.
        Args:
            camera_index (int): Index of the camera to use (default: 0).
        """
        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(self.camera_index)
        self.image = None
        self.width = 0
        self.height = 0
        self.x_min = 0
        self.x_max = 0
        self.y_min = 0
        self.y_max = 0

        if not self.cap.isOpened():
            raise ValueError(f"Unable to access camera at index {self.camera_index}")

        # Get initial frame dimensions
        ret, frame = self.cap.read()
        if ret:
            self.height, self.width, _ = frame.shape
            self.update_coordinate_bounds()

    def update_coordinate_bounds(self):
        """
        Update the map's coordinate bounds based on the current image dimensions.
        """
        self.x_min = -self.width / (2 * SCALE_FACTOR)
        self.x_max = self.width / (2 * SCALE_FACTOR)
        self.y_min = -self.height / (2 * SCALE_FACTOR)
        self.y_max = self.height / (2 * SCALE_FACTOR)

    def capture_image(self):
        """
        Capture an image from the camera.
        """
        ret, frame = self.cap.read()
        if ret:
            self.image = frame
            print("Image captured.")
        else:
            print("Failed to capture image.")

    def display_image(self):
        """
        Display the most recently captured image.
        """
        if self.image is not None:
            cv2.imshow("Camera Feed", self.image)
            cv2.waitKey(1)
        else:
            print("No image to display.")

    def map_to_pixel(self, x, y):
        """
        Convert world coordinates to pixel coordinates.
        """
        pixel_x = int((x * SCALE_FACTOR) + (self.width / 2))
        pixel_y = int((-y * SCALE_FACTOR) + (self.height / 2))
        return pixel_x, pixel_y

    def pixel_to_map(self, pixel_x, pixel_y):
        """
        Convert pixel coordinates to world coordinates.
        """
        x = (pixel_x - (self.width / 2)) / SCALE_FACTOR
        y = -((pixel_y - (self.height / 2)) / SCALE_FACTOR)
        return x, y

    def release_camera(self):
        """
        Release the camera resource.
        """
        self.cap.release()
        cv2.destroyAllWindows()

    def capture_periodically(self, interval=1):
        """
        Capture images periodically at a specified interval (in seconds).
        Args:
            interval (int): Time between captures in seconds (default: 1).
        """
        try:
            while True:
                self.capture_image()
                self.display_image()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Stopping periodic capture.")
            self.release_camera()
