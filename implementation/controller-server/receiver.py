import asyncio
import json
import multiprocessing
from websockets import connect

# This function handles incoming messages from the WebSocket server
async def websocket_receiver(message_bus, spheros):
    try:
        # Establish a WebSocket connection to the server
        async with connect("ws://localhost:8080") as ws:
            print("WebSocket: Connected to the server.\n")

            # Send an initialization message to identify this client as a Sphero controller
            await ws.send(json.dumps({"clientType": "SpheroController", "messageType": "SpheroConnection", "spheros": spheros}))
            print("WebSocket: Sent connection initialization.\n")

            while True:
                try:
                    # Receive a message from the WebSocket server
                    message = await ws.recv()
                    print(f"WebSocket: Received message: {message} \n")

                    # Parse the message (convert it from JSON string to a Python dictionary)
                    parsed_message = json.loads(message)

                    # Find the target Sphero's ID from the message
                    target_id = parsed_message["id"]

                    # If the target ID exists in the message bus, add the message to the bus
                    if target_id in message_bus:
                        message_bus[target_id].append(message)

                except Exception as e:
                    print(f"WebSocket: Error receiving message: {e}\n")
                    break
    except Exception as e:
        print(f"WebSocket: Connection error: {e}\n")
    finally:
        print("WebSocket: Closing connection.\n")


# This function handles sending messages from the outgoing queue back to the WebSocket server
async def websocket_sender(outgoing_queue):
    try:
        # Establish a WebSocket connection to the server for sending messages
        async with connect("ws://localhost:8080") as ws:
            print("WebSocket Sender: Connected to the server.\n")

            while True:
                try:
                    # Check if there are any messages in the outgoing queue
                    if not outgoing_queue.empty():
                        message = outgoing_queue.get()

                        # Send the message to the WebSocket server
                        await ws.send(json.dumps(message))
                        print(f"WebSocket Sender: Sent message: {message}\n")
                except Exception as e:
                    print(f"WebSocket Sender: Error sending message: {e}\n")
                    break
    except Exception as e:
        print(f"WebSocket Sender: Connection error: {e}\n")
    finally:
        print("WebSocket Sender: Closing connection.\n")


# This function adds a message to the outgoing queue to be sent to the WebSocket server
def send_message_to_server(outgoing_queue, id, messageType, message):
    try:
        # Create the message in a dictionary format
        message_json = {
            "clientType": "SpheroController",
            "id": id,
            "messageType": messageType,
            "message": message
        }

        # Add the message to the outgoing queue
        outgoing_queue.put(message_json)
        print(f"Message added to outgoing queue: {message_json}\n")
    except Exception as e:
        print(f"Error adding message to outgoing queue: {e}\n")


# This function processes incoming messages for a specific Sphero
def process_subscriber(client_id, message_bus, outgoing_queue):
    print(f"{client_id}: Subscribed to message bus.\n")
    while True:
        try:
            # Check if there are messages for this Sphero in the message bus
            if message_bus[client_id]:
                # Get and parse the first message from the bus
                parsed_message = json.loads(message_bus[client_id].pop(0))

                # Extract the type and content of the message
                message_type = parsed_message["messageType"]
                message_content = parsed_message["message"]

                # Handle the message based on its type
                handle_message(client_id, message_type, message_content, outgoing_queue)
        except Exception as e:
            print(f"{client_id}: Error in subscriber: {e}\n")
            break


# This function tells the Sphero to move and sends feedback
def move(id, path, outgoing_queue):
    # Print the movement path for the Sphero
    print(f"I am moving Sphero {id} to {path}\n")

    # Add feedback to the outgoing queue
    send_message_to_server(outgoing_queue, id, "SpheroFeedback", "Done")


# This function decides what to do with incoming messages based on their type
def handle_message(id, message_type, message, outgoing_queue):
    match message_type:
        case "SpheroMovement":
            move(id, message, outgoing_queue)
        case _:
            print(f"Sphero {id}: Unhandled message type: {message_type}\n")


# This function starts the WebSocket connection
def run_websocket(message_bus, spheros):
    asyncio.run(websocket_receiver(message_bus, spheros))


# This function starts the WebSocket sender
def run_websocket_sender(outgoing_queue):
    asyncio.run(websocket_sender(outgoing_queue))


if __name__ == "__main__":
    with multiprocessing.Manager() as manager:
        spheros = [
            {"id": "Alpha", "color": "#000"},
            {"id": "Beta", "color": "#FFF"},
            {"id": "Sigma", "color": "#111"},
            {"id": "Rho", "color": "#BBB"},
        ]

        message_bus = manager.dict({sphero["id"]: manager.list() for sphero in spheros})
        outgoing_queue = manager.Queue()

        websocket_process = multiprocessing.Process(target=run_websocket, args=(message_bus, spheros))
        websocket_sender_process = multiprocessing.Process(target=run_websocket_sender, args=(outgoing_queue,))

        subscriber_processes = [
            multiprocessing.Process(target=process_subscriber, args=(sphero["id"], message_bus, outgoing_queue))
            for sphero in spheros
        ]

        websocket_process.start()
        websocket_sender_process.start()

        for process in subscriber_processes:
            process.start()

        websocket_process.join()
        websocket_sender_process.join()
        for process in subscriber_processes:
            process.join()
