import threading
import cv2

class Display:
    mouse_x = 0
    mouse_y = 0

    def __init__(self):
        """
        Initialize the Display class to manage image display and drawing functionality.
        """
        self.image = None  # Current image to be displayed
        self.width = None  # Width of the current image
        self.height = None  # Height of the current image
        self.drawings = []  # List to store drawing instructions (e.g., points, lines, rectangles)
        self.lock = threading.Lock()  # Lock for thread-safe operations
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

    def draw_point(self, id, x, y, weight, color):
        """
        Draw a visualization for a specific object on the display using the color from the color map.
        Args:
            id: Unique identifier for the object.
            x: X-coordinate.
            y: Y-coordinate.
            weight: Weight or size of the object.
            color: The color in hex.
        """
        # Convert hex to BGR
        color = self.hex_to_bgr(color)

        with self.lock:
            # Remove any existing drawings with the same ID
            self.drawings = [drawing for drawing in self.drawings if drawing["id"] != id]
            # Add the new drawing with the specified color
            self.drawings.append({"id": id, "x": x, "y": y, "weight": weight, "color": color})

    def draw_line(self, id, point1, point2, weight, color):
        """
        Draw a line between two points on the display.

        Args:
            id: Unique identifier for the line.
            point1: Tuple (x1, y1) representing the start of the line.
            point2: Tuple (x2, y2) representing the end of the line.
            weight: Thickness of the line.
            color: The color in hex.
        """
        color = self.hex_to_bgr(color)  # Convert hex color to BGR

        with self.lock:
            # Remove any existing drawings with the same ID
            self.drawings = [drawing for drawing in self.drawings if drawing["id"] != id]
            # Add the new line drawing
            self.drawings.append({
                "id": id,
                "start": point1,
                "end": point2,
                "weight": weight,
                "color": color
            })

    def draw_rectangle(self, id, x, y, w, h, weight, color):
        """
        Draw a rectangle on the display.

        Args:
            id: Unique identifier for the rectangle.
            x, y: Top-left corner of the rectangle.
            w, h: Width and height of the rectangle.
            weight: Thickness of the rectangle edges.
            color: The color in hex format.
        """
        color = self.hex_to_bgr(color)  # Convert hex color to BGR

        with self.lock:
            # Remove any existing drawings with the same ID
            self.drawings = [drawing for drawing in self.drawings if drawing["id"] != id]
            # Add the new rectangle drawing
            self.drawings.append({
                "id": id,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "weight": weight,
                "color": color
            })

    @staticmethod
    def mouse_callback(event, x, y, flags, param):
        """
        Mouse callback to update mouse_x, mouse_y when moving the cursor over the display window.
        """
        if event == cv2.EVENT_MOUSEMOVE:
            Display.mouse_x = x
            Display.mouse_y = y

    def show(self):
        """
        Continuously display the current image with any drawings.
        """
        cv2.namedWindow("Display")
        cv2.setMouseCallback("Display", self.mouse_callback)

        while self.running:
            image = self.get_image()
            if image is not None:
                with self.lock:
                    overlay_image = image.copy()

                    # Draw all the overlays
                    for drawing in self.drawings:
                        if "x" in drawing and "y" in drawing and "w" in drawing and "h" in drawing:  # Rectangle
                            x = int(drawing["x"])
                            y = int(drawing["y"])
                            w = int(drawing["w"])
                            h = int(drawing["h"])
                            weight = max(1, int(drawing["weight"] * 5))  # Scale thickness
                            color = drawing["color"]  # Use the specified color (BGR)

                            cv2.rectangle(
                                overlay_image,
                                (x, y),  # Top-left corner
                                ( x + w, y + h),  # Bottom-right corner
                                color=color,
                                thickness=weight
                            )
                        elif "x" in drawing and "y" in drawing:  # Point
                            x = int(drawing["x"])
                            y = int(drawing["y"])
                            radius = int(drawing["weight"] * 50)  # Example scaling
                            color = drawing["color"]

                            cv2.circle(
                                overlay_image,
                                (y, x),  # Note: (y, x) order in OpenCV for display
                                radius=radius,
                                color=color,
                                thickness=2
                            )
                        elif "start" in drawing and "end" in drawing:  # Line
                            start_x, start_y = drawing["start"]
                            end_x, end_y = drawing["end"]

                            weight = max(1, min(int(drawing["weight"] * 5), 255))  # Scale and clamp thickness
                            color = drawing["color"]

                            cv2.line(
                                overlay_image,
                                (int(start_y), int(start_x)),  # (y, x)
                                (int(end_y), int(end_x)),  # (y, x)
                                color=color,
                                thickness=weight
                            )

                # Display mouse coordinates on the image
                mouse_text = f"X: {self.mouse_x}, Y: {self.mouse_y}"
                cv2.putText(
                    overlay_image,
                    mouse_text,
                    (10, 30),  # Position in the image (x, y)
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,  # Font scale
                    (255, 255, 255),  # White text
                    2  # Thickness
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
