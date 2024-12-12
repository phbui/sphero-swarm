import threading
import cv2

class Display:
    mouse_x = 0
    mouse_y = 0
    mouse_x_original = 0
    mouse_y_original = 0

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

    def show(self):
        """
        Continuously display the current image with any drawings.
        """
        cv2.namedWindow("Display")

        while self.running:
            image = self.get_image()
            if image is not None:
                with self.lock:
                    overlay_image = image.copy()

                    # Resize overlay image to half the dimensions
                    half_width = self.width // 2
                    half_height = self.height // 2
                    overlay_image = cv2.resize(overlay_image, (half_width, half_height))

                    # Scale factors for mapping coordinates back to the original
                    scale_x = self.width / half_width
                    scale_y = self.height / half_height

                    # Update mouse callback with scaling factors
                    cv2.setMouseCallback("Display", self.mouse_callback, {"scale_x": scale_x, "scale_y": scale_y})

                    # Draw all the overlays
                    for drawing in self.drawings:
                        if "x" in drawing and "y" in drawing and "w" in drawing and "h" in drawing:  # Rectangle
                            scaled_x = int(drawing["x"] / scale_x)
                            scaled_y = int(drawing["y"] / scale_y)
                            scaled_w = int(drawing["w"] / scale_x)
                            scaled_h = int(drawing["h"] / scale_y)
                            thickness = 1
                            color = drawing["color"]
                            cv2.rectangle(
                                overlay_image,
                                (scaled_x, scaled_y),  # Top-left corner
                                (scaled_x + scaled_w, scaled_y + scaled_h),  # Bottom-right corner
                                color=color,
                                thickness=thickness
                            )
                        elif "x" in drawing and "y" in drawing:  # Point
                            scaled_x = int(drawing["x"] / scale_x)
                            scaled_y = int(drawing["y"] / scale_y)
                            radius = int(drawing["weight"] * 50)  # Example scaling
                            color = drawing["color"]
                            cv2.circle(
                                overlay_image,
                                (scaled_y, scaled_x), # OpenCV format (y, x)
                                radius=radius,
                                color=color,
                                thickness=2
                            )
                        elif "start" in drawing and "end" in drawing:  # Line
                            start_x = int(drawing["start"][0] / scale_x)
                            start_y = int(drawing["start"][1] / scale_y)
                            end_x = int(drawing["end"][0] / scale_x)
                            end_y = int(drawing["end"][1] / scale_y)
                            thickness = 1
                            color = drawing["color"]
                            cv2.line(
                                overlay_image,
                                (start_y, start_x),  # Start point
                                (end_y, end_x),  # End point
                                color=color,
                                thickness=thickness
                            )

                    # Display mouse coordinates
                    mouse_text = f"Y: {Display.mouse_y_original}, X: {Display.mouse_x_original}"
                    cv2.putText(
                        overlay_image,
                        mouse_text,
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0,
                        (255, 255, 255),
                        2
                    )

                    # Show the resized image
                    cv2.imshow("Display", overlay_image)

                if cv2.waitKey(1) & 0xFF == ord('q'):  # Press 'q' to quit
                    self.running = False
                    break
            else:
                cv2.waitKey(100)

    @staticmethod
    def mouse_callback(event, x, y, flags, param):
        """
        Mouse callback to update mouse coordinates relative to the original image dimensions.
        """
        if event == cv2.EVENT_MOUSEMOVE:
            Display.mouse_x = x
            Display.mouse_y = y

            if param:
                Display.mouse_x_original = int(x * param["scale_x"])
                Display.mouse_y_original = int(y * param["scale_y"])
            else:
                Display.mouse_x_original = x
                Display.mouse_y_original = y

    def stop(self):
        """
        Stop the display loop and close the window.
        """
        self.running = False
        cv2.destroyAllWindows()
