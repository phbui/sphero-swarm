const WebSocket = require("ws");

// Create a WebSocket server on port 8080
const wss = new WebSocket.Server({ port: 8080 });
console.log("WebSocket server is running on ws://localhost:8080");

// List of connected clients
let clients = [];
let spheros = [];

/**
 * Handles the connection of a general client (non-SpheroController).
 * Adds the client to the `clients` list.
 * @param {WebSocket} ws - The WebSocket connection.
 * @param {string} clientType - The type of client connecting.
 */
function handleConnection(ws, clientType) {
  console.log("Client connected: " + clientType);
  clients.push({ clientType: clientType, id: clientType, ws: ws });
}

/**
 * Handles the connection of a SpheroController and its associated Spheros.
 * Adds each Sphero to the `clients` list.
 * @param {WebSocket} ws - The WebSocket connection.
 * @param {Array} spheroList - List of Sphero objects being controlled.
 */
function handleControllerConnection(ws, spheroList) {
  spheros = spheroList;
  spheroList.forEach((sphero) => {
    console.log(`Client connected: [SpheroController]: ${sphero.id}`);
    clients.push({ clientType: "SpheroController", id: sphero.id, ws: ws });
  });
  intializeSpheros();
}

/**
 * Handles the connection of the Brain Server.
 * Adds the Brain Server to the `clients` list.
 * @param {WebSocket} ws - The WebSocket connection.
 */
function handleBrainConnection(ws) {
  console.log(`Client connected: [SpheroBrain]`);
  clients.push({ clientType: "SpheroBrain", id: "SpheroBrain", ws: ws });
  intializeSpheros();
}

/**
 * Initializes the Spheros by notifying the Brain Server of their connection.
 */
function intializeSpheros() {
  if (spheros.length > 0) {
    sendMessageToClient("SpheroBrain", "SpheroConnection", spheros);
  }
}

/**
 * Notifies the Brain Server that all Spheros are ready.
 */
function readyBrain() {
  if (spheros.length > 0) {
    sendMessageToClient("SpheroBrain", "SpheroReady", {});
  }
}

/**
 * Sends a message to a specific client.
 * @param {string} id - The ID of the target client.
 * @param {string} messageType - The type of the message being sent.
 * @param {any} message - The content of the message.
 */
function sendMessageToClient(id, messageType, message) {
  const client = clients.find((c) => c.id === id);
  if (client && client.ws.readyState === WebSocket.OPEN) {
    client.ws.send(
      JSON.stringify({ id: id, messageType: messageType, message: message })
    );
    console.log(`Message sent to ${id}: ${JSON.stringify(message)}`);
  } else {
    console.log(`${id} not found or not connected.`);
  }
}

/**
 * Sends a movement command to a specific Sphero.
 * @param {string} id - The ID of the Sphero to move.
 * @param {number} current_x - Current x-coordinate of the Sphero.
 * @param {number} current_y - Current y-coordinate of the Sphero.
 * @param {number} target_x - Target x-coordinate for the Sphero.
 * @param {number} target_y - Target y-coordinate for the Sphero.
 * @param {number} last_x - Last x-coordinate the Sphero moved to.
 * @param {number} last_y - Last y-coordinate the Sphero moved to.
 */
function moveSphero(
  id,
  current_x,
  current_y,
  target_x,
  target_y,
  last_x,
  last_y
) {
  sendMessageToClient(id, "SpheroMovement", {
    currentLocation: [current_x, current_y],
    targetLocation: [target_x, target_y],
    lastTargetLocation: [last_x, last_y],
  });
}

/**
 * Sends an LED matrix pattern to all connected Spheros.
 */
function matrixCall() {
  clients.forEach((client) => {
    if (
      client &&
      client.clientType === "SpheroController" &&
      client.ws.readyState === WebSocket.OPEN
    ) {
      sendMessageToClient(client.id, "SpheroMatrix", "X");
    }
  });
}

/**
 * Marks a specific Sphero as ready and checks if all Spheros are ready.
 * @param {string} sphero_id - The ID of the Sphero.
 * @returns {boolean} True if all Spheros are ready, otherwise false.
 */
function handleReady(sphero_id) {
  const sphero = spheros.find((s) => s.id === sphero_id);

  if (!sphero) {
    console.error(`Sphero with id ${sphero_id} not found.`);
    return false;
  }

  console.log(`[Sphero ${sphero_id}] Ready!`);

  sphero.ready = true;

  const allReady = spheros.every((s) => s.ready);

  return allReady;
}

/**
 * Processes messages from SpheroControllers.
 * @param {WebSocket} ws - The WebSocket connection.
 * @param {Object} parsedMessage - The message received from the client.
 */
function handleControllerMessage(ws, parsedMessage) {
  let messageType = parsedMessage.messageType;

  switch (messageType) {
    case "SpheroConnection":
      let spheroList = parsedMessage.spheros;
      handleControllerConnection(ws, spheroList);
      break;

    case "SpheroReady":
      let sphero_id = parsedMessage.id;
      if (handleReady(sphero_id)) {
        readyBrain();
      }
      break;

    case "SpheroFeedback":
      sendMessageToClient(
        "SpheroBrain",
        "SpheroFeedback",
        parsedMessage.message
      );
      break;
  }
}

/**
 * Processes messages from the Brain Server.
 * @param {WebSocket} ws - The WebSocket connection.
 * @param {Object} parsedMessage - The message received from the Brain Server.
 */
function handleBrainMessage(ws, parsedMessage) {
  let messageType = parsedMessage.messageType;

  switch (messageType) {
    case "BrainConnection":
      handleBrainConnection(ws);
      break;

    case "BrainControl":
      let message = parsedMessage.message;
      moveSphero(
        message.id,
        message.current_x,
        message.current_y,
        message.target_x,
        message.target_y,
        message.last_x,
        message.last_y
      );
      break;
  }
}

/**
 * Routes incoming messages to the appropriate handler based on the client type.
 * @param {WebSocket} ws - The WebSocket connection.
 * @param {Object} parsedMessage - The message received from the client.
 */
function handleClientMessage(ws, parsedMessage) {
  let clientType = parsedMessage.clientType;

  switch (clientType) {
    case "SpheroController":
      handleControllerMessage(ws, parsedMessage);
      break;
    case "SpheroBrain":
      handleBrainMessage(ws, parsedMessage);
      break;
    default:
      handleConnection(ws, clientType);
      break;
  }
}

// Listen for new WebSocket connections
wss.on("connection", (ws) => {
  ws.on("message", (message) => {
    let parsedMessage = JSON.parse(message.toString());
    try {
      handleClientMessage(ws, parsedMessage);
    } catch (e) {
      console.log(`Error processing message: ${e}`);
    }
  });

  ws.on("close", () => {
    console.log("A client has disconnected.");
    clients = clients.filter((client) => client.ws !== ws);
  });
});
