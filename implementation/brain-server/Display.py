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

    def set_image(self, image):
        """
        Set the current image to be displayed and update dimensions.
        Args:
            image: The image to set.
        """
        with self.lock:
            self.image = image
            if image is not None:
                self.height, self.width = image.shape[:2]  # Dynamically update dimensions

    def get_image(self):
        """
        Get the current image being displayed.
        Returns:
            The current image.
        """
        with self.lock:
            return self.image
        
    def hex_to_bgr(self, hex_color):
        """
        Convert a hex color code to BGR format.

        Args:
            hex_color (str): The hex color code as a string (e.g., "#RRGGBB").

        Returns:
            tuple: A tuple representing the BGR color (Blue, Green, Red).
        """
        hex_color = hex_color.lstrip('#')  # Remove the '#' if present
        if len(hex_color) != 6:
            raise ValueError(f"Invalid hex color: {hex_color}")
        
        # Convert hex to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        # Return as BGR (OpenCV format)
        return (b, g, r)

    def draw(self, id, x, y, weight, color):
        """
        Draw a visualization for a specific object on the display using the color from the color map.
        Args:
            id: Unique identifier for the object.
            x: X-coordinate.
            y: Y-coordinate.
            weight: Weight or size of the object.
            color: The color in hex.
        """
        # Get the color from the COLOR_MAP dictionary
        color = self.hex_to_bgr(color) # Default to black if not found
        
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
            image = self.get_image()
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

                # Resize the overlay image to max half the screen width while maintaining the aspect ratio
                screen_width = 1920
                max_width = screen_width // 2
                
                original_height, original_width = overlay_image.shape[:2]
                aspect_ratio = original_height / original_width

                if original_width > max_width:
                    new_width = max_width
                    new_height = int(new_width * aspect_ratio)
                    overlay_image = cv2.resize(overlay_image, (new_width, new_height))

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
