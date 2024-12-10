import asyncio
import json
import Planner
from websockets import connect

class WebSocketHandler:
    def __init__(self):
        self.planner = None
        self.lock = asyncio.Lock()

    async def handle_message(self, ws, id, message_type, message):
        """Handles incoming messages and initializes Planner when a SpheroConnection is received."""
        async with self.lock:  # Acquire lock before modifying or accessing planner
            match message_type:
                case "SpheroConnection":
                    print(f"Received SpheroConnection message: {message}")
                    spheros = message
                    self.planner = Planner.Planner(spheros)
                case "SpheroReady":
                    print("Starting planner.")
                    self.planner.start(ws)  

                case "SpheroFeedback":
                    print("Executing next move.")
                    self.planner.next_move(ws, message)  

    async def websocket_receiver(self):
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
                            await self.handle_message(
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

# Main function
async def main():
    handler = WebSocketHandler()
    await handler.websocket_receiver()

if __name__ == "__main__":
    asyncio.run(main())
