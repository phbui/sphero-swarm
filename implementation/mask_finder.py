import cv2
import numpy as np
import time
import json

# Define initial color ranges in HSV format
color_ranges = {           
    #'#FF00FF': ([120, 0, 230], [150, 255, 255]),  # Pink
    #'#FF0000': ([5, 45, 60], [30, 255, 255]),  # Red
    #'#035900': ([80, 115, 65], [95, 255, 255]),  # Green
    #'#020082': ([70, 20, 180], [180, 100, 255]),  # Blue
    #'#FFFF00': ([50, 0, 245], [80, 80, 255])  # Yellow
    'Obstacles': ([5, 135, 60], [20, 255, 240]),
    'Goal':([125, 115, 100],[130, 140, 130]) 
}

# Define colors for visualization
color_map = {
    '#FF00FF': (255, 0, 255),  # Pink
    '#FF0000': (0, 0, 255),      # Red
    '#035900': (0, 255, 0),      # Green
    '#020082': (255, 255, 0),    # Dark Blue
    '#FFFF00': (0, 255, 255) ,     # Yellow
    'Obstacles': (255, 255, 255),
    'Goal': (255, 255, 255) 
}

# Function to create trackbars for HSV range adjustment
def create_trackbars(color_hex, initial_lower, initial_upper):
    cv2.namedWindow(f"Settings for {color_hex}")
    cv2.createTrackbar("H_Low", f"Settings for {color_hex}", initial_lower[0], 179, nothing)
    cv2.createTrackbar("S_Low", f"Settings for {color_hex}", initial_lower[1], 255, nothing)
    cv2.createTrackbar("V_Low", f"Settings for {color_hex}", initial_lower[2], 255, nothing)
    cv2.createTrackbar("H_High", f"Settings for {color_hex}", initial_upper[0], 179, nothing)
    cv2.createTrackbar("S_High", f"Settings for {color_hex}", initial_upper[1], 255, nothing)
    cv2.createTrackbar("V_High", f"Settings for {color_hex}", initial_upper[2], 255, nothing)

# Function to get current trackbar positions
def get_trackbar_values(color_hex):
    h_low = cv2.getTrackbarPos("H_Low", f"Settings for {color_hex}")
    s_low = cv2.getTrackbarPos("S_Low", f"Settings for {color_hex}")
    v_low = cv2.getTrackbarPos("V_Low", f"Settings for {color_hex}")
    h_high = cv2.getTrackbarPos("H_High", f"Settings for {color_hex}")
    s_high = cv2.getTrackbarPos("S_High", f"Settings for {color_hex}")
    v_high = cv2.getTrackbarPos("V_High", f"Settings for {color_hex}")
    return (h_low, s_low, v_low), (h_high, s_high, v_high)

# Function to save current settings
def save_settings(filename="color_settings.json"):
    settings = {}
    for color_hex, _ in color_ranges.items():
        settings[color_hex] = get_trackbar_values(color_hex)
    with open(filename, 'w') as f:
        json.dump(settings, f, indent=2)

# Dummy function for trackbar callbacks
def nothing(x):
    pass

# Create trackbars for each color with initial values
for color_hex, (lower_bound, upper_bound) in color_ranges.items():
    create_trackbars(color_hex, lower_bound, upper_bound)


# Open the default camera
cap = cv2.VideoCapture(0)

# Capture and save an image every 5 seconds
last_capture_time = time.time()

while(True):
    # Capture frame-by-frame
    ret, frame = cap.read()

    if not ret:
        print("Error: Unable to capture frame from camera.")
        break

    # Convert BGR to HSV
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Create a black background for the combined image
    combined_image = np.zeros_like(frame) 

    for color_hex, _ in color_ranges.items():
        # Get current trackbar positions
        (h_low, s_low, v_low), (h_high, s_high, v_high) = get_trackbar_values(color_hex)
        lower = np.array([h_low, s_low, v_low], dtype=np.uint8)
        upper = np.array([h_high, s_high, v_high], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)

        # Apply the color to the mask
        color_mask = np.zeros_like(frame)
        color_mask[mask > 0] = color_map[color_hex] 

        # Combine the colored mask with the combined image
        combined_image = cv2.addWeighted(combined_image, 1, color_mask, 1, 0)

        # Find contours in the mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) > 0:
            # Find the contour with the largest area (most concentrated)
            largest_contour = max(contours, key=cv2.contourArea)
            # Find the center of the largest contour
            M = cv2.moments(largest_contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                cv2.putText(combined_image, color_hex, (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2) 

    # Display the combined image with labels
    cv2.imshow("Color Masks", combined_image)

    # Save settings on 's' key press
    if cv2.waitKey(1) & 0xFF == ord('s'):
        save_settings()

    # Exit on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()