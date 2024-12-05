import asyncio
import json
import Planner
from websockets import connect

# WebSocket Receiver and Handler
async def websocket_receiver():
    global planner  # Planner instance to be initialized dynamically
    try:
        async with connect("ws://localhost:8080") as ws:
            print("WebSocket: Connected to the server.\n")

            # Send initialization message to identify the client
            await ws.send(json.dumps({"clientType": "SpheroBrain", "messageType": "BrainConnection"}))
            print("WebSocket: Sent connection initialization.\n")

            while True:
                try:
                    # Receive and process messages in real-time
                    message = await ws.recv()
                    print(f"WebSocket: Received message: {message} \n")

                    try:
                        parsed_message = json.loads(message)
                        
                        # Ensure parsed_message is a dictionary
                        if not isinstance(parsed_message, dict):
                            raise ValueError("Parsed message is not a dictionary.")
                        
                        # Extract and validate required keys
                        required_keys = ["id", "messageType", "message"]
                        if not all(key in parsed_message for key in required_keys):
                            raise KeyError(f"Message missing required keys. Received: {parsed_message}")

                        # Handle the message
                        await handle_message(
                            ws,
                            parsed_message["id"],
                            parsed_message["messageType"],
                            parsed_message["message"],
                        )
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        print(f"WebSocket: Malformed message: {e}")
                except Exception as e:
                    print(f"WebSocket: Error processing message: {e}\n")
    except Exception as e:
        print(f"WebSocket: Connection error: {e}\n")
    finally:
        print("WebSocket: Closing connection.\n")

# Handle messages by type
async def handle_message(ws, id, message_type, message):
    """Handles incoming messages and initializes Planner when a SpheroConnection is received."""
    global planner
    match message_type:
        case "SpheroConnection":
            print(f"Received SpheroConnection message: {message}")
            spheros = message
            planner = Planner.Planner(spheros) 
            print("Starting planner.")
            planner.start()
        case "SpheroReady":
            print("Ready!")
        case "SpheroFeedback":
            planner.next_move(ws, message)
        case _:
            print(f"Sphero {id}: Unhandled message type: {message_type}")


# Send messages to WebSocket server
async def send_message(ws, id, message_type, message_content):
    """Sends a message to the WebSocket server."""
    try:
        message = {
            "clientType": "SpheroBrain",
            "id": id,
            "messageType": message_type,
            "message": message_content,
        }
        await ws.send(json.dumps(message))
        print(f"WebSocket: Sent message: {message}")
    except Exception as e:
        print(f"WebSocket: Error sending message: {e}")


# Main function
async def main():
    await websocket_receiver()


if __name__ == "__main__":
    # Global Planner instance (initialized dynamically after SpheroConnection)
    planner = None
    asyncio.run(main())
