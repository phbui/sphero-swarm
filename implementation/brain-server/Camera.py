import cv2

SCALE_FACTOR = 50  # 1 unit of distance = 50 pixels

class Camera:
    def __init__(self, display, camera_index=0):
        """
        Initialize the Camera class.
        Args:
            display (Display): The display instance to update.
            camera_index (int): Index of the camera to use (default: 0).
        """
        self.display = display  # Reference to a Display instance for visualization
        self.camera_index = camera_index  # Camera index for accessing the video stream
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)  # Initialize camera capture
        self.width = 0  # Width of the camera frame
        self.height = 0  # Height of the camera frame
        self.x_min = 0  # Minimum x-coordinate in world units
        self.x_max = 0  # Maximum x-coordinate in world units
        self.y_min = 0  # Minimum y-coordinate in world units
        self.y_max = 0  # Maximum y-coordinate in world units

        if not self.cap.isOpened():
            raise ValueError(f"Unable to access camera at index {self.camera_index}")

        # Get initial frame dimensions
        ret, frame = self.cap.read()
        if ret:
            self.height, self.width, _ = frame.shape  # Set the frame dimensions
            self.update_coordinate_bounds()  # Update the coordinate bounds based on dimensions
        else:
            raise ValueError("Failed to capture initial frame from camera.")

    def update_coordinate_bounds(self):
        """
        Update the map's coordinate bounds based on the current image dimensions.
        """
        self.x_min = -self.width / (2 * SCALE_FACTOR)  # Convert pixel width to world units
        self.x_max = self.width / (2 * SCALE_FACTOR)  # Convert pixel width to world units
        self.y_min = -self.height / (2 * SCALE_FACTOR)  # Convert pixel height to world units
        self.y_max = self.height / (2 * SCALE_FACTOR)  # Convert pixel height to world units

    def capture_image(self):
        """
        Capture an image from the camera and update the display.
        Returns:
            frame (numpy.ndarray): Captured frame from the camera.
        """
        ret, frame = self.cap.read()

        for _ in range(5):
            ret, frame = self.cap.read()

        if ret:
            self.display.set_image(frame)  # Update the display with the captured frame
            return frame
        else:
            print("Failed to capture image.")

    def release_camera(self):
        """
        Release the camera resource.
        """
        self.cap.release()  # Release the camera to free system resources
