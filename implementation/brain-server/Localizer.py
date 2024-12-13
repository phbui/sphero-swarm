import numpy as np
import cv2
from sklearn.mixture import GaussianMixture
import Particle
from color_ranges import color_ranges

class Localizer:
    def __init__(self, camera, display, color, num_particles):
        """
        Initialize the Localizer class.
        Args:
            camera: Camera instance for capturing images.
            display: Display instance for visualization.
            color: Target color for localization (hex format).
            num_particles: Number of particles to use in the particle filter.
        """
        try:
            self.camera = camera  # Reference to the camera instance
            self.display = display  # Reference to the display instance
            self.color = color  # Target color for tracking
            self.num_particles = num_particles  # Number of particles for tracking

            # Initialize particles
            self.particles = [Particle.Particle(display, color) for _ in range(num_particles)]
        except Exception as e:
            print(f"Error initializing Localizer: {e}")

    def updateParticles(self):
        """
        Update particle positions and weights based on the detected target color region.
        Returns:
            Tuple (gmm_y, gmm_x): Coordinates of the Gaussian Mixture Model (GMM) mean.
        """
        try:
            # Capture the current frame
            image = self.camera.capture_image()
            height, width = image.shape[:2]  # Extract height and width from the image

            # Extract the region of interest (mask) based on the target color
            mask = self._getColorMask(image, self.color)
            points = np.column_stack(np.where(mask > 0))  # Extract pixel coordinates

            # Fit a Gaussian Mixture Model to the color region
            if len(points) > 0:
                # Calculate the geometric center of the points (unweighted mean)
                geometric_center = np.mean(points, axis=0)  # Average of all points

                # Fit a Gaussian Mixture Model initialized at the geometric center
                gmm = GaussianMixture(
                    n_components=1,
                    means_init=[geometric_center]  # Initialize mean to the geometric center
                ).fit(points)

                # Retrieve GMM mean and covariance
                gmm_y, gmm_x = gmm.means_[0]
                cov = gmm.covariances_[0]
                cov += np.eye(2) * 1e-6  # Ensure covariance matrix is not singular

                for particle in self.particles:
                    if particle.x == 0 and particle.y == 0:
                        particle.x = np.random.normal(gmm_x, np.sqrt(cov[0, 0]))
                        particle.y = np.random.normal(gmm_y, np.sqrt(cov[1, 1]))
                        particle.weight = 1.0 / len(self.particles)
            else:
                # Handle case when no points are detected
                gmm_y, gmm_x = height // 2, width // 2   # Default to image center
                cov = np.eye(2)  # Default covariance

            # Update particle weights based on the GMM
            for particle in self.particles:
                gmm_weight = self._calculateWeight(particle.x, particle.y, (gmm_x, gmm_y), cov)
                particle.weight = gmm_weight

            # Normalize weights
            self._normalizeWeights()

            # Check if all weights are zero after normalization
            total_weight = sum(p.weight for p in self.particles)
            if total_weight == 0:
                for particle in self.particles:
                    particle.weight = 1.0 / len(self.particles)

            # Resample and move particles
            self._resampleAndMoveParticles(gmm_y, gmm_x)

            return gmm_y, gmm_x
        except Exception as e:
            print(f"Error updating particles: {e}")
            return None, None

    def _calculateWeight(self, x, y, mean, cov):
        """
        Calculate particle weight using a Gaussian likelihood function.
        Args:
            x, y: Particle coordinates.
            mean: Mean position as a tuple (x, y).
            cov: Covariance matrix.
        Returns:
            Weight as a float.
        """
        try:
            if mean is None:
                return 0
            mean = np.array(mean)
            pos = np.array([x, y])
            cov += np.eye(2) * 1e-6  # Add small value to diagonal for stability
            inv_cov = np.linalg.inv(cov)
            diff = pos - mean
            weight = np.exp(-0.5 * diff @ inv_cov @ diff.T) / (2 * np.pi * np.sqrt(np.linalg.det(cov)))
            return weight
        except Exception as e:
            return 0


    def _resampleAndMoveParticles(self, mean_y, mean_x):
        """
        Resample particles based on their weights and move them closer to the detected mean.
        Args:
            mean_x: X-coordinate of the detected mean.
            mean_y: Y-coordinate of the detected mean.
        """
        try:
            weights = [p.weight for p in self.particles]

            # Handle case where all weights are zero
            if sum(weights) == 0:
                for particle in self.particles:
                    particle.move(np.random.uniform(0, self.display.width),
                                  np.random.uniform(0, self.display.height),
                                  1 / self.num_particles)
                return

            # Resample indices based on weights
            resampled_indices = np.random.choice(
                len(self.particles), size=self.num_particles, p=weights
            )

            # Move particles to the positions of the resampled ones, biased towards the mean
            for i, particle in enumerate(self.particles):
                resampled_particle = self.particles[resampled_indices[i]]

                # Move towards the mean with some Gaussian noise
                noise_x = np.random.normal(0, 5)  # Adjust noise level as needed
                noise_y = np.random.normal(0, 5)

                new_x = 0.7 * resampled_particle.x + 0.3 * mean_x + noise_x  # Weighted towards mean
                new_y = 0.7 * resampled_particle.y + 0.3 * mean_y + noise_y

                particle.move(new_y, new_x, resampled_particle.weight / 4)
        except Exception as e:
            print(f"Error in resampling and moving particles: {e}")

    def _getColorMask(self, image, color):
        """
        Generate a binary mask isolating the target color.
        Args:
            image: Input image in BGR format.
            color: Target color in hex format.
        Returns:
            Binary mask isolating the target color.
        """
        try:
            hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)  # Convert image to HSV color space
            lower_bound, upper_bound = self._getColorBounds(color)  # Get color bounds
            mask = cv2.inRange(hsv_image, lower_bound, upper_bound)  # Generate mask

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            # Debug coordinates:
            #moments = cv2.moments(mask)
            #if moments["m00"] > 0:
            #    center_x = int(moments["m10"] / moments["m00"])
            #    center_y = int(moments["m01"] / moments["m00"])
            #else:
            #    center_x, center_y = -1, -1

            # Create a black background and overlay the mask
            #screen_width = 1920
            #screen_height = 1080
            #quarter_width = screen_width // 4
            #quarter_height = screen_height // 4

            #black_background = np.zeros((quarter_height, quarter_width), dtype=np.uint8)
            #mask_resized = cv2.resize(mask, (quarter_width, quarter_height))
            #overlay_image = cv2.merge((black_background, mask_resized, black_background))  # Optional: convert to 3 channels if needed

            #if center_x >= 0 and center_y >= 0:
            #    scaled_center_x = int(center_x * (quarter_width / mask.shape[1]))
            #    scaled_center_y = int(center_y * (quarter_height / mask.shape[0]))

                # Add a label with coordinates to the overlay image
            #    cv2.circle(overlay_image, (scaled_center_x, scaled_center_y), 5, (0, 255, 0), -1)  # Green dot
            #    label = f"({center_y}, {center_x})"
            #    cv2.putText(
            #        overlay_image,
            #        label,
            #        (scaled_center_x + 10, scaled_center_y - 10),  # Offset for readability
            #        cv2.FONT_HERSHEY_SIMPLEX,
            #        0.5,  # Font scale
            #        (0, 255, 0),  # Green color
            #        1,  # Thickness
            #        cv2.LINE_AA
            #    )

            # Display the mask non-blocking
            #cv2.imshow(f"Mask {color} for {lower_bound} - {upper_bound}", overlay_image)
            #cv2.waitKey(1)  # Non-blocking, updates the display without halting execution

            return mask
        except Exception as e:
            print(f"Error generating color mask: {e}")
            return None

    def _getColorBounds(self, color):
        """
        Return the lower and upper HSV bounds for the target color.
        Args:
            color: Target color in hex format.
        Returns:
            Tuple (lower_bound, upper_bound) for the color in HSV.
        """
        try:
            if color in color_ranges:
                lower, upper = color_ranges[color]
                return np.array(lower, dtype=np.uint8), np.array(upper, dtype=np.uint8)
            else:
                raise ValueError(f"Color '{color}' is not defined in color ranges.")
        except Exception as e:
            print(f"Error getting color bounds: {e}")
            return None, None

    def _normalizeWeights(self):
        """
        Normalize particle weights to sum to 1.
        """
        try:
            total_weight = sum(p.weight for p in self.particles)
            if total_weight > 0:
                for particle in self.particles:
                    particle.weight /= total_weight
        except Exception as e:
            print(f"Error normalizing weights: {e}")
