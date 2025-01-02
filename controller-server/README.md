# Controller Server for Sphero Swarm BLE Connections

This server is part of a larger microservice architecture designed to control concurrent Bluetooth Low Energy (BLE) connections to Sphero drones. It serves as the **Controller Server**, responsible for managing swarm connections, executing movement instructions, and handling feedback from the Sphero devices based on commands from the Brain Server.

## Features

- **Concurrent Sphero Control:** Manages multiple BLE connections to control a swarm of Sphero robots.
- **WebSocket Communication:** Interfaces with the Brain Server for receiving movement instructions and sending feedback.
- **Flexible Movement Commands:** Supports directional movement, matrix pattern setting, and precise location targeting.
- **Dynamic Feedback:** Provides real-time updates about the Sphero’s state to the Brain Server.

## Architecture

This Controller Server integrates several components:

### Components

1. **SpheroMovement**

   - Provides an abstraction for controlling individual Sphero robots.
   - Supports directional movement, position-based navigation, and LED matrix pattern setting.

2. **MySpheroEduAPI**

   - Extends the SpheroEduAPI library to fix and enhance LED matrix functionality.

3. **WebSocket Communication**

   - Manages incoming instructions from the Brain Server.
   - Sends feedback about the current state and movements of the Sphero robots.

4. **Multiprocessing Architecture**

   - Utilizes Python's `multiprocessing` module to handle multiple Sphero connections concurrently.

## Dependencies

- Python 3.8+
- `numpy`
- `websockets`
- `spherov2`
- `pillow`
- `bleak`

## Code Overview

### Key Files

- **`sphero_movement.py`**: Provides the `SpheroMovement` class to control Sphero robots, including movement, LED matrix patterns, and feedback.
- **`sphero_subclass.py`**: Extends and fixes functionalities in the SpheroEduAPI library, particularly for drawing lines on the LED matrix.
- **`receiver.py`**: Handles WebSocket communication, processes commands from the Brain Server, and manages multiprocessing for concurrent Sphero connections.

### System Flow

1. **Initialization**: The server identifies available Sphero devices and establishes BLE connections.
2. **Command Processing**: WebSocket messages from the Brain Server are parsed and mapped to specific Sphero devices.
3. **Execution**: Commands like movement or matrix updates are executed using the `SpheroMovement` class.
4. **Feedback**: Feedback is sent back to the Brain Server to synchronize further instructions.

## Supported Commands

1. **SpheroMovement**

   - Move to a specific location based on current and target coordinates.

2. **Directional Movement**

   - Commands such as `MoveNorth`, `MoveSouth`, `MoveEast`, `MoveWest` for moving in cardinal directions.

3. **LED Matrix Patterns**

   - Draw patterns like an `X` on the LED matrix using `SpheroMatrix` commands.

4. **Feedback**
   - Sends status updates such as `SpheroReady` and completion of movement commands.

## Logging

The server logs all activity, including WebSocket communication, Sphero commands, and errors. Logs are saved to `sphero_controller.log` and displayed in the console.
