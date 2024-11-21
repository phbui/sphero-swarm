const WebSocket = require("ws");

// Create a WebSocket server on port 8080
const wss = new WebSocket.Server({ port: 8080 });
console.log("WebSocket server is running on ws://localhost:8080");

// List of connected clients
let clients = [];

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
 * @param {Array} spheros - List of Sphero objects being controlled.
 */
function handleSpheroConnection(ws, spheros) {
  spheros.forEach((sphero) => {
    console.log(`Client connected: [SpheroController]: ${sphero.id}`);
    clients.push({ clientType: "SpheroController", id: sphero.id, ws: ws });
  });
}

/**
 * Sends a message to a specific client.
 * @param {string} id - The ID of the target client.
 * @param {string} messageType - The type of the message being sent.
 * @param {any} message - The content of the message.
 */
function sendMessageToClient(id, messageType, message) {
  const client = clients.find((c) => c.id === id); // Find the client by ID
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
 * @param {Array} path - A list of coordinate pairs for the Sphero to follow.
 */
function moveSphero(id, path) {
  sendMessageToClient(id, "SpheroMovement", path);
}

/**
 * Generates three random coordinate pairs within a given range.
 * @param {number} range - The maximum value for x and y coordinates.
 * @returns {Array} An array of 3 coordinate pairs.
 */
function generateRandomCoordinatePairs(range = 100) {
  return Array.from({ length: 3 }, () => {
    return [Math.random() * range, Math.random() * range];
  });
}

/**
 * Sends random movement commands to all connected Spheros.
 * This is called every 5 seconds.
 */
function moveSpheroRandomly() {
  clients.forEach((client) => {
    if (
      client &&
      client.clientType === "SpheroController" &&
      client.ws.readyState === WebSocket.OPEN
    ) {
      moveSphero(client.id, generateRandomCoordinatePairs());
    }
  });
}

// Call moveSpheroRandomly every 5 seconds
setInterval(moveSpheroRandomly, 5000);

/**
 * Handles messages sent by SpheroControllers.
 * Processes different message types such as "SpheroConnection" and "SpheroFeedback".
 * @param {WebSocket} ws - The WebSocket connection.
 * @param {Object} parsedMessage - The message received from the client.
 */
function handleSpheroControllerMessage(ws, parsedMessage) {
  let messageType = parsedMessage.messageType;

  switch (messageType) {
    case "SpheroConnection": // SpheroController is connecting its Spheros
      let spheros = parsedMessage.spheros;
      handleSpheroConnection(ws, spheros);
      break;

    case "SpheroFeedback": // Feedback from a SpheroController
      console.log(parsedMessage);
      break;
  }
}

/**
 * Handles messages from any client.
 * Routes the message to the correct handler based on client type.
 * @param {WebSocket} ws - The WebSocket connection.
 * @param {Object} parsedMessage - The message received from the client.
 */
function handleClientConnection(ws, parsedMessage) {
  let clientType = parsedMessage.clientType;

  switch (clientType) {
    case "SpheroController": // If the client is a SpheroController
      handleSpheroControllerMessage(ws, parsedMessage);
      break;

    default: // General client connection
      handleConnection(ws, clientType);
      break;
  }
}

// Listen for new WebSocket connections
wss.on("connection", (ws) => {
  // Handle incoming messages from clients
  ws.on("message", (message) => {
    let parsedMessage = JSON.parse(message.toString());
    try {
      handleClientConnection(ws, parsedMessage);
    } catch (e) {
      console.log(`Error processing message: ${e}`);
    }
  });

  // Remove the client from the `clients` list when they disconnect
  ws.on("close", () => {
    console.log("A client has disconnected.");
    clients = clients.filter((client) => client.ws !== ws);
  });
});
