import threading
import cv2

COLOR_MAP = {
    'red': (0, 0, 255),     # Red in BGR
    'blue': (255, 0, 0),    # Blue in BGR
    'green': (0, 255, 0),   # Green in BGR
    'yellow': (0, 255, 255) # Yellow in BGR
}

class Display:
    def __init__(self):
        self.image = None
        self.width = None
        self.height = None
        self.drawings = []
        self.lock = threading.Lock()
        self.running = True  # Controls the display loop

    def setImage(self, image):
        """
        Set the current image to be displayed and update dimensions.
        Args:
            image: The image to set.
        """
        with self.lock:
            self.image = image
            if image is not None:
                self.height, self.width = image.shape[:2]  # Dynamically update dimensions

    def getImage(self):
        """
        Get the current image being displayed.
        Returns:
            The current image.
        """
        with self.lock:
            return self.image

    def draw(self, id, x, y, weight, color_name):
        """
        Draw a visualization for a specific object on the display using the color from the color map.
        Args:
            id: Unique identifier for the object.
            x: X-coordinate.
            y: Y-coordinate.
            weight: Weight or size of the object.
            color_name: The color name ('red', 'blue', 'green', 'yellow').
        """
        # Get the color from the COLOR_MAP dictionary
        color = COLOR_MAP.get(color_name.lower(), (0, 0, 0))  # Default to black if not found
        
        with self.lock:
            # Remove any existing drawings with the same ID
            self.drawings = [drawing for drawing in self.drawings if drawing["id"] != id]
            # Add the new drawing with the specified color
            self.drawings.append({"id": id, "x": x, "y": y, "weight": weight, "color": color})

    def show(self):
        """
        Continuously display the current image with any drawings.
        """
        while self.running:
            image = self.getImage()
            if image is not None:
                with self.lock:
                    # Create a copy to draw overlays on
                    overlay_image = image.copy()

                    # Draw all the overlays
                    for drawing in self.drawings:
                        # Ensure x and y are integers for cv2.circle
                        x = int(drawing["x"])
                        y = int(drawing["y"])
                        radius = int(drawing["weight"] * 50)  # Example scaling
                        color = drawing["color"]  # Use the specified color (in BGR)

                        cv2.circle(
                            overlay_image,
                            (y, x),  # Pass the integer coordinates
                            radius=radius,
                            color=color,  # Use the specified color
                            thickness=2
                        )

                # Show the image in a window
                cv2.imshow("Display", overlay_image)
                if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to quit
                    self.running = False
                    break
            else:
                # If no image is set, wait briefly before checking again
                cv2.waitKey(100)

    def stop(self):
        """
        Stop the display loop and close the window.
        """
        self.running = False
        cv2.destroyAllWindows()
