# Brain Server for Sphero Drone Localization and Path Planning

This server is part of a larger architecture of microservices for probabilistic Monte Carlo Localization (MCL) and Probabilistic Roadmap (PRM) generation. It serves as the **Brain Server**, responsible for real-time localization, mapping, and collision-aware path planning for Sphero drones.

## Features

- **Monte Carlo Localization (MCL):** Tracks Sphero drones using color detection and particle filters.
- **Probabilistic Roadmap (PRM):** Generates a roadmap of nodes and edges to plan paths around obstacles.
- **Collision-Aware Movement:** Plans and adjusts movements to avoid detected obstacles.
- **WebSocket Communication:** Interfaces with other microservices and clients in the system architecture.

## Architecture

This Brain Server integrates several components:

### Components

1. **Camera**

   - Captures real-time images for obstacle and Sphero detection.
   - Provides coordinate mapping for visualization.

2. **Display**

   - Visualizes captured images, detected objects, and planned paths.
   - Handles mouse interactions and threading for real-time updates.

3. **Map**

   - Processes captured images to detect obstacles and generate PRM nodes and edges.
   - Calculates obstacle weights for collision avoidance.

4. **Localizer**

   - Tracks Sphero positions using Gaussian Mixture Models (GMM) and particle filters.

5. **Drone**

   - Represents individual Sphero drones.
   - Implements a state machine for navigation and interaction.

6. **Planner**

   - Coordinates `Camera`, `Display`, `Map`, and `Drone` components.
   - Manages the system pipeline for path planning and Sphero control.

7. **WebSocketHandler**
   - Handles communication with the WebSocket server.
   - Manages incoming messages and integrates with the Planner.

## Dependencies

- Python 3.8+
- `opencv-python`
- `websockets`
- `scikit-learn`
- `numpy`
- `scipy`

## Usage

- The server waits for WebSocket messages to initialize and manage Spheros.
- Messages:
  - **`SpheroConnection`:** Initializes the `Planner` with Sphero IDs and colors.
  - **`SpheroReady`:** Starts the Planner.
  - **`SpheroFeedback`:** Updates the Planner with Sphero feedback for the next move.

## Code Overview

### Key Files

- **`Camera.py`**: Manages image capture and coordinate mapping.
- **`Display.py`**: Provides visualization and interaction.
- **`Map.py`**: Detects obstacles and generates PRMs.
- **`Localizer.py`**: Tracks Spheros using MCL.
- **`Drone.py`**: Implements drone state machines and navigation.
- **`Planner.py`**: Coordinates components for mapping and control.
- **`receiver.py`**: Handles WebSocket communication.

### System Flow

1. **Initialization**: WebSocket receives `SpheroConnection` message to set up Spheros.
2. **Planning**: Planner initializes PRM and prepares navigation paths.
3. **Execution**: WebSocket receives `SpheroReady` and starts the navigation loop.
4. **Feedback**: WebSocket receives `SpheroFeedback` to know when the previous move is finished and when to start the next one.
