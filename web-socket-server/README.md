# WebSocket Server for Sphero Microservice Architecture

This server is part of a larger microservice architecture that connects all components of the system, including the **Brain Server** and the **Controller Server**, which manage Sphero swarm control and movement. The WebSocket Server acts as the central communication hub, facilitating seamless message exchange between these services.

## Features

- **Centralized Communication:** Connects the Brain Server and Controller Server for synchronized operations.
- **Real-Time Messaging:** Enables low-latency communication for movement commands and feedback.
- **Multi-Client Support:** Handles multiple clients, including Brain and Controller services, simultaneously.
- **Dynamic Command Routing:** Routes movement commands and feedback between the appropriate services and devices.

## Architecture

The WebSocket Server is a critical component of the Sphero microservice ecosystem:

### Components

1. **Client Connections**

   - Supports connections from Brain Server, Controller Server, and other potential clients.
   - Identifies clients by type (e.g., `SpheroController`, `SpheroBrain`).

2. **Message Handling**

   - Processes incoming messages and routes them to the appropriate clients.
   - Handles commands such as movement, readiness checks, and LED matrix updates.

3. **Sphero Initialization**

   - Manages the initialization of Sphero devices by notifying the Brain Server when Spheros are connected and ready.

4. **Command Execution**
   - Routes commands like `SpheroMovement` from the Brain Server to the Controller Server.
   - Handles feedback from the Controller Server and forwards it to the Brain Server.

## Dependencies

- Node.js
- `ws` (WebSocket library)

## Code Overview

### Key Files

- **`server.js`**: Implements the WebSocket server, managing client connections and message routing.

### System Flow

1. **Client Connection**: The server accepts WebSocket connections from the Brain Server, Controller Server, and other clients.
2. **Initialization**: The Controller Server connects its Sphero devices, and the Brain Server is notified of available Spheros.
3. **Command Routing**: The Brain Server sends movement commands to specific Spheros via the Controller Server.
4. **Feedback Handling**: The Controller Server provides feedback on Sphero actions, which is forwarded to the Brain Server.

## Supported Commands

1. **SpheroConnection**

   - Initializes the connection with the Controller Server and its Sphero devices.

2. **SpheroMovement**

   - Moves a specific Sphero based on current and target coordinates.

3. **SpheroReady**

   - Notifies the Brain Server when all Spheros are ready for commands.

4. **SpheroFeedback**

   - Sends feedback from the Controller Server to the Brain Server about Sphero actions.

5. **SpheroMatrix**
   - Updates the LED matrix on a Sphero to display specific patterns (e.g., an `X`).

## Logging

The server logs all activity, including connection events, command routing, and errors. Logs are displayed in the console.
