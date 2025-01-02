# Sphero Microservice Architecture: Brain Server, Controller Server, and WebSocket Server

This project is a comprehensive microservice architecture designed to manage Sphero swarm robots using **probabilistic Monte Carlo Localization (MCL)** and **Probabilistic Roadmap (PRM)** for real-time path planning and movement control. The system comprises the following core components:

1. **Brain Server**: Handles localization, mapping, and high-level path planning.
2. **Controller Server**: Manages Bluetooth Low Energy (BLE) connections to Sphero devices, executing movement and feedback.
3. **WebSocket Server**: Acts as a communication hub, routing commands and feedback between the Brain and Controller servers.

## Features

- **Monte Carlo Localization (MCL)**: Tracks Sphero positions using particle filters and Gaussian Mixture Models (GMM).
- **Probabilistic Roadmap (PRM)**: Plans collision-aware paths using a network of nodes and edges.
- **Real-Time Communication**: WebSocket-based message exchange for low-latency operations.
- **Concurrent Sphero Control**: Manages multiple BLE connections and robot movements simultaneously.

## Architecture Overview

### 1. **Brain Server**

The Brain Server is responsible for high-level operations:

- Capturing images via the `Camera` component.
- Visualizing paths and obstacles using `Display`.
- Detecting obstacles and generating PRMs through the `Map` component.
- Tracking Sphero positions with `Localizer`.
- Coordinating path planning with `Planner`.

### 2. **Controller Server**

The Controller Server handles:

- Establishing BLE connections to Spheros.
- Executing movement commands via the `SpheroMovement` class.
- Providing feedback on movement and LED matrix updates.
- Multiprocessing for concurrent Sphero operations.

### 3. **WebSocket Server**

The WebSocket Server acts as the central communication hub:

- Routes movement commands and feedback between the Brain and Controller servers.
- Manages client connections and initialization.

## Communication Flow

### Initialization

1. The **Controller Server** connects to Spheros via BLE and registers them with the WebSocket Server.
2. The WebSocket Server notifies the **Brain Server** about available Spheros.
3. The Brain Server begins PRM generation and localization.

### Command Execution

1. The Brain Server sends movement commands (e.g., `SpheroMovement`) to the WebSocket Server.
2. The WebSocket Server forwards these commands to the Controller Server.
3. The Controller Server executes the commands using BLE and provides feedback.
4. Feedback is routed back to the Brain Server via the WebSocket Server for synchronization.

## Installation

To ensure a smooth installation experience:

1. **Run as Admin**: Right-click the application icon and select "Run as admin."
2. **Install Requirements**: Run the `requirements.bat` file to install all dependencies.

```bash
requirements.bat
```

3. **Start Servers**: Use the `run.bat` file to start all servers (Brain, Controller, and WebSocket).

```bash
run.bat
```

## Key Components

### Brain Server

- **Files**:
  - `Camera.py`: Captures images for localization.
  - `Display.py`: Visualizes paths, obstacles, and drone locations.
  - `Drone.py`: Manages each Sphero and their state machine.
  - `Map.py`: Detects obstacles and generates PRMs.
  - `Localizer.py`: Tracks Sphero locations using MCL.
  - `Paricle.py`: Manages particles for `Localizer.py`.
  - `Planner.py`: Coordinates path planning and drone navigation.
  - `receiver.py`: Manages WebSocket communication and multiprocessing for Sphero control.

### Controller Server

- **Files**:
  - `sphero_movement.py`: Executes Sphero movements and LED matrix updates.
  - `sphero_subclass.py`: Extends SpheroEduAPI for enhanced LED matrix control.
  - `receiver.py`: Manages WebSocket communication and multiprocessing for Sphero control.

### WebSocket Server

- **Files**:
  - `server.js`: Routes messages between Brain and Controller servers.

## Usage

1. **Initialization**:

   - The WebSocket Server listens for connections on `ws://localhost:8080`.
   - The Controller Server registers its Spheros, and the Brain Server is notified of available devices.

2. **Command Processing**:

   - Movement commands (`SpheroMovement`) and feedback are routed through the WebSocket Server.
   - LED matrix updates (`SpheroMatrix`) are triggered via the Controller Server.

3. **Execution**:
   - Commands are executed by the Sphero devices using BLE.
   - Feedback ensures synchronization between servers.

## Logging

All servers log activity for monitoring and debugging:

- **Brain Server**: Logs PRM generation, localization, and path planning.
- **Controller Server**: Logs BLE connections, movement execution, and feedback.
- **WebSocket Server**: Logs client connections, message routing, and errors.
