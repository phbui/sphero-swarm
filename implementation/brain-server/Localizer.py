import numpy as np
import cv2
from sklearn.mixture import GaussianMixture
import Particle

# Define color ranges for target detection in HSV format
color_ranges = {
    '#0000FF': ([140, 200, 200], [160, 255, 255]),  # Blue
    '#FF0000': ([170, 110, 165], [180, 220, 245]),  # Red
    '#008000': ([40, 120, 100], [80, 255, 255]),    # Green
    '#00FFFF': ([85, 100, 100], [100, 255, 255]),  # Cyan
    '#DFFF00': ([20, 200, 200], [45, 255, 255])     # Yellow
}

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
        self.camera = camera  # Reference to the camera instance
        self.display = display  # Reference to the display instance
        self.color = color  # Target color for tracking
        self.num_particles = num_particles  # Number of particles for tracking

        # Initialize particles
        self.particles = [Particle.Particle(display, color) for _ in range(num_particles)]

    def updateParticles(self):
        """
        Update particle positions and weights based on the detected target color region.
        Returns:
            Tuple (gmm_x, gmm_y): Coordinates of the Gaussian Mixture Model (GMM) mean.
        """
        # Capture the current frame
        image = self.camera.capture_image()
        height, width = image.shape[:2]  # Extract height and width from the image

        # Extract the region of interest (mask) based on the target color
        mask = self._getColorMask(image, self.color)
        points = np.column_stack(np.where(mask > 0))  # Extract pixel coordinates

        # Fit a Gaussian Mixture Model to the color region
        if len(points) > 0:
            gmm = GaussianMixture(n_components=1).fit(points)
            gmm_x, gmm_y = gmm.means_[0]
            cov = gmm.covariances_[0]
        else:
            # Handle edge case if no points are detected
            gmm_x, gmm_y = width // 2, height // 2  # Default to center
            cov = np.eye(2)  # Default covariance

        # Update particle weights based on the GMM
        for particle in self.particles:
            particle_x, particle_y = particle.x, particle.y
            particle.weight = self._calculateWeight(particle_x, particle_y, (gmm_x, gmm_y), cov)

        # Normalize weights
        self._normalizeWeights()

        # Resample and move particles
        self._resampleAndMoveParticles(gmm_x, gmm_y)

        return gmm_x, gmm_y

    def _resampleAndMoveParticles(self, mean_x, mean_y):
        """
        Resample particles based on their weights and move them closer to the detected mean.
        Args:
            mean_x: X-coordinate of the detected mean.
            mean_y: Y-coordinate of the detected mean.
        """
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

            particle.move(new_x, new_y, resampled_particle.weight)

    def _getColorMask(self, image, color):
        """
        Generate a binary mask isolating the target color.
        Args:
            image: Input image in BGR format.
            color: Target color in hex format.
        Returns:
            Binary mask isolating the target color.
        """
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)  # Convert image to HSV color space
        lower_bound, upper_bound = self._getColorBounds(color)  # Get color bounds
        mask = cv2.inRange(hsv_image, lower_bound, upper_bound)  # Generate mask

        # Clean up the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        return mask

    def _getColorBounds(self, color):
        """
        Return the lower and upper HSV bounds for the target color.
        Args:
            color: Target color in hex format.
        Returns:
            Tuple (lower_bound, upper_bound) for the color in HSV.
        """
        if color in color_ranges:
            lower, upper = color_ranges[color]
            return np.array(lower, dtype=np.uint8), np.array(upper, dtype=np.uint8)
        else:
            raise ValueError(f"Color '{color}' is not defined in color ranges.")

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
        if mean is None:
            return 0
        mean = np.array(mean)
        pos = np.array([x, y])
        inv_cov = np.linalg.inv(cov)
        diff = pos - mean
        weight = np.exp(-0.5 * diff @ inv_cov @ diff.T) / (2 * np.pi * np.sqrt(np.linalg.det(cov)))
        return weight

    def _normalizeWeights(self):
        """
        Normalize particle weights to sum to 1.
        """
        total_weight = sum(p.weight for p in self.particles)
        if total_weight > 0:
            for particle in self.particles:
                particle.weight /= total_weight
