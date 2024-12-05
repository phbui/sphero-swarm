import cv2
import time

SCALE_FACTOR = 50  # 1 unit of distance = 50 pixels

class Camera:
    def __init__(self, display, camera_index=0):
        """
        Initialize the Camera class.
        Args:
            display (Display): The display instance to update.
            camera_index (int): Index of the camera to use (default: 0).
        """
        self.display = display
        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(self.camera_index)
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
        else:
            raise ValueError("Failed to capture initial frame from camera.")

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
        Capture an image from the camera and update the display.
        """
        ret, frame = self.cap.read()
        if ret:
            print("Image captured.")
            self.display.setImage(frame)  # Update the display with the captured frame
        else:
            print("Failed to capture image.")

    def release_camera(self):
        """
        Release the camera resource.
        """
        self.cap.release()
