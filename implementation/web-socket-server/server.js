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
 * @param {Array} sphespheroListros - List of Sphero objects being controlled.
 */
function handleControllerConnection(ws, spheroList) {
  spheros = spheroList;
  spheroList.forEach((sphero) => {
    console.log(`Client connected: [SpheroController]: ${sphero.id}`);
    clients.push({ clientType: "SpheroController", id: sphero.id, ws: ws });
  });
  intializeSpheros();
}

function handleBrainConnection(ws) {
  console.log(`Client connected: [SpheroBrain]`);
  clients.push({ clientType: "SpheroBrain", id: "SpheroBrain", ws: ws });
  intializeSpheros();
}

function intializeSpheros() {
  if (spheros.length > 0) {
    sendMessageToClient("SpheroBrain", "SpheroConnection", spheros);
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
 * @param {Array} path - A list of coordinate pairs for the Sphero to follow.
 */
function moveSphero(id, current_x, current_y, target_x, target_y) {
  sendMessageToClient(id, "SpheroMovement", {
    currentLocation: [current_x, current_y],
    targetLocation: [target_x, target_y],
  });
}

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

setInterval(matrixCall,60000)

/**
 * Handles messages sent by SpheroControllers.
 * Processes different message types such as "SpheroConnection" and "SpheroFeedback".
 * @param {WebSocket} ws - The WebSocket connection.
 * @param {Object} parsedMessage - The message received from the client.
 */
function handleControllerMessage(ws, parsedMessage) {
  let messageType = parsedMessage.messageType;

  switch (messageType) {
    case "SpheroConnection": // SpheroController is connecting its Spheros
      let spheroList = parsedMessage.spheros;
      handleControllerConnection(ws, spheroList);
      break;

    case "SpheroFeedback": // Feedback from a SpheroController
      sendMessageToClient("SpheroBrain", "SpheroFeedback", "Done");
      break;
  }
}

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
        message.target_y
      );
      break;
  }
}

function handleClientMessage(ws, parsedMessage) {
  let clientType = parsedMessage.clientType;

  switch (clientType) {
    case "SpheroController":
      handleControllerMessage(ws, parsedMessage);
      break;
    case "SpheroBrain":
      handleBrainMessage(ws, parsedMessage);
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
      handleClientMessage(ws, parsedMessage);
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
