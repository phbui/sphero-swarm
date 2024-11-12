const WebSocket = require("ws");

// Check CLI arguments to decide which server to run
const args = process.argv.slice(2);
const mode = args[0] || "face"; // Default to "face" if no argument is given

const face_ServerUrl = "ws://localhost:8081";
const scan_ServerUrl = "ws://localhost:8082";
let socket;

const wss = new WebSocket.Server({ port: 8080 });
console.log("WebSocket server is running on ws://localhost:8080");

// Store connections for ESP32 clients
let clients = [];

function handleConnection(clientType, id, ws) {
  console.log("Client connected: " + clientType);
  console.log("Id: " + id);
  clients.push({ clientType: clientType, ws: ws });
  notifyOpen();
}

function handleLog(clientType, message) {
  let log = JSON.parse(message.toString()).message;
  console.log(`Message from ${clientType}: ${log}`);
}

function notifyOpen() {
  if (socket.readyState === WebSocket.OPEN) {
    clients.forEach((client) => {
      if (client.ws.readyState === WebSocket.OPEN) {
        client.ws.send(
          JSON.stringify({
            id: "run",
            message: "Begin",
          })
        );
        console.log("Sent 'Begin' to esp32 clients.");
      }
    });
  }
}

// Function to connect to the specified WebSocket server based on CLI argument
function connectToServer() {
  switch (mode) {
    case "face":
      socket = new WebSocket(face_ServerUrl);
      console.log("Connecting to face recognition server...");
      break;
    case "scan":
      socket = new WebSocket(scan_ServerUrl);
      console.log("Connecting to scan server...");
      break;
    default:
      console.error(`Invalid mode specified: ${mode}. Use "face" or "scan".`);
      process.exit(1);
  }

  // Send "Begin" to all esp32 clients when connected
  socket.on("open", () => {
    console.log(
      `Connected to ${mode === "face" ? "face recognition" : "scan"} server.`
    );

    notifyOpen();
  });

  socket.on("error", (error) => {
    console.error(`Error connecting to ${mode} server: ${error}`);
  });

  // Send "End" to all esp32 clients before reconnecting
  socket.on("close", () => {
    clients.forEach((client) => {
      if (client.ws.readyState === WebSocket.OPEN) {
        client.ws.send(
          JSON.stringify({
            id: "run",
            message: "End",
          })
        );
        console.log("Sent 'End' to esp32 clients.");
      }
    });
    console.log(`Disconnected from ${mode} server. Reconnecting...`);
    setTimeout(connectToServer, 5000); // Reconnect after 5 seconds
  });
}

// Handle client connections
wss.on("connection", (ws) => {
  ws.on("message", (message) => {
    try {
      let clientType = JSON.parse(message.toString()).clientType;
      let id = JSON.parse(message.toString()).id;

      switch (clientType) {
        case "esp32-cam":
          switch (id) {
            case "start":
              handleConnection(clientType, id, ws);
              break;
            case "binaryImage":
              //console.log("Received binary message (image data)");
              let binaryImageBase64 = JSON.parse(
                message.toString()
              ).binaryImage;
              let binaryImageBuffer = Buffer.from(binaryImageBase64, "base64");

              if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(binaryImageBuffer);
                //console.log(`Forwarded image to ${mode} server.`);
              } else {
                /* console.log(
                  `The ${mode} server is not connected. Cannot forward image.`
                ); */
              }
              break;
            case "log":
              handleLog(clientType, message);
              break;
          }
          break;
        case "esp32-controller":
          switch (id) {
            case "start":
              handleConnection(clientType, id, ws);
              break;
            case "log":
              handleLog(clientType, message);
              break;
          }
          break;
        case "python-face":
          switch (id) {
            case "start":
              handleConnection(clientType, id, ws);
              break;
            case "faceData":
              let faceData = JSON.parse(message.toString()).faceData;
              clients.forEach((client) => {
                if (
                  client.clientType === "esp32-controller" &&
                  client.ws.readyState === WebSocket.OPEN
                ) {
                  let message = JSON.stringify({
                    id: "control",
                    message: faceData,
                  });
                  client.ws.send(message);
                  //console.log(`Sent ${message} to esp32-control client.`);
                }
              });
              break;
          }
          break;
      }
    } catch (e) {
      console.log(`Error: ${e}`);
    }
  });

  // Handle client disconnection
  ws.on("close", () => {
    console.log("A client has disconnected.");
    clients = clients.filter((client) => client.ws !== ws); // Remove disconnected clients
  });
});

// Start the connection based on CLI argument
connectToServer();
