import asyncio
import json
import multiprocessing
from websockets import connect
from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
from PIL import ImageColor
import time
import logging
from sphero_movement import SpheroMovement  # Import the movement class
import signal
import sys

active_spheros = []

# Signal handler for graceful shutdown
def shutdown_handler(signal_received, frame):
    logging.info("Signal received, shutting down...")
    for toy in active_spheros:
        try:
            toy.stop_roll()  # Stop movement if any
            toy.set_main_led(Color(0, 0, 0))  # Turn off the LED
            toy.close()  # Close the connection
            logging.info(f"Disconnected Sphero {toy.toy.name}.")
        except Exception as e:
            logging.error(f"Error disconnecting Sphero: {e}")
    sys.exit(0)

# Register the signal handler
signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("sphero_controller.log"),
        logging.StreamHandler()
    ]
)

# This function handles incoming messages from the WebSocket server
async def websocket_receiver(message_bus, spheros):
    try:
        async with connect("ws://localhost:8080") as ws:
            logging.info("WebSocket: Connected to the server.")
            await ws.send(json.dumps({"clientType": "SpheroController", "messageType": "SpheroConnection", "spheros": spheros}))
            logging.info("WebSocket: Sent connection initialization.")

            while True:
                try:
                    message = await ws.recv()
                    logging.info(f"WebSocket: Received message: {message}")
                    parsed_message = json.loads(message)
                    target_id = parsed_message["id"]

                    if target_id in message_bus:
                        message_bus[target_id].append(message)
                except Exception as e:
                    logging.error(f"WebSocket: Error receiving message: {e}")
                    break
    except Exception as e:
        logging.error(f"WebSocket: Connection error: {e}")
    finally:
        logging.warning("WebSocket: Closing connection.")

# This function handles sending messages from the outgoing queue back to the WebSocket server
async def websocket_sender(outgoing_queue):
    try:
        async with connect("ws://localhost:8080") as ws:
            logging.info("WebSocket Sender: Connected to the server.")
            while True:
                try:
                    if not outgoing_queue.empty():
                        message = outgoing_queue.get()
                        await ws.send(json.dumps(message))
                        logging.info(f"WebSocket Sender: Sent message: {message}")
                except Exception as e:
                    logging.error(f"WebSocket Sender: Error sending message: {e}")
                    break
    except Exception as e:
        logging.error(f"WebSocket Sender: Connection error: {e}")
    finally:
        logging.warning("WebSocket Sender: Closing connection.")

# Add a message to the outgoing queue
def send_message_to_server(outgoing_queue, id, messageType, message):
    try:
        message_json = {
            "clientType": "SpheroController",
            "id": id,
            "messageType": messageType,
            "message": message
        }
        outgoing_queue.put(message_json)
        logging.info(f"Message added to outgoing queue: {message_json}")
    except Exception as e:
        logging.error(f"Error adding message to outgoing queue: {e}")

# This function processes incoming messages for a specific Sphero
def process_subscriber(client_id, client_color, message_bus, outgoing_queue, toy):
    logging.info(f"{client_id}: Subscribed to message bus.")
    while True:
        try:
            if message_bus[client_id]:
                parsed_message = json.loads(message_bus[client_id].pop(0))
                message_type = parsed_message["messageType"]
                message_content = parsed_message["message"]
                handle_message(client_id, client_color, message_type, message_content, outgoing_queue, toy)
        except Exception as e:
            logging.error(f"{client_id}: Error in subscriber: {e}")

# This function handles specific messages for the Sphero
def handle_message(id, client_color, message_type, message, outgoing_queue, toy):
    sphero = SpheroMovement(toy, id, client_color, outgoing_queue)  # Create a movement instance

    if message_type == "SpheroMovement":
        current = message["currentLocation"]
        target = message["targetLocation"]
        sphero.move(current, target)

    elif message_type == "MoveNorth":
        sphero.move_direction("north", message)

    elif message_type == "MoveSouth":
        sphero.move_direction("south", message)

    elif message_type == "MoveWest":
        sphero.move_direction("west", message)

    elif message_type == "MoveEast":
        sphero.move_direction("east", message)

    elif message_type == "SpheroMatrix":
        sphero.set_matrix(message)

    else:
        logging.warning(f"Sphero {id}: Unhandled message type: {message_type}")

# This function runs the Sphero connection and processes messages
def run_sphero(client_id, client_color, message_bus, outgoing_queue, first_run=False):
    logging.info(f"{client_id}: Attempting to connect.")
    rgb = ImageColor.getrgb(client_color)
    client_color = Color(r=rgb[0], g=rgb[1], b=rgb[2])

    while True:  # Retry loop
        toy = None

        # Attempt to find and connect to the Sphero
        while toy is None:
            try:
                toy = scanner.find_toy(toy_name=client_id)
                logging.info(f"{client_id}: Connected to Sphero.")
            except scanner.ToyNotFoundError:
                logging.warning(f"{client_id}: Sphero not found. Ensure it is powered on and in range. Retrying...")
                time.sleep(5)
            except Exception as e:
                logging.error(f"{client_id}: Unexpected error: {e}")
                time.sleep(5)

        try:
            with SpheroEduAPI(toy) as droid:
                active_spheros.append(droid)  # Add to the active Spheros list
                if first_run:
                    logging.info(f"{client_id}: Calibrating compass.")
                    droid.calibrate_compass()
                    droid.set_compass_direction(0)
                droid.set_main_led(client_color)
                logging.info(f"{client_id}: Initialization complete.")
                process_subscriber(client_id, client_color, message_bus, outgoing_queue, toy)

        except Exception as e:
            logging.error(f"{client_id}: Failed to initialize or maintain connection to Sphero: {e}")

        finally:
            # Clean up and prepare for retry
            if toy in active_spheros:
                active_spheros.remove(toy)
            logging.warning(f"{client_id}: Sphero connection closed. Retrying...")
            time.sleep(5)  # Retry delay before attempting to reconnect

# WebSocket processes
def run_websocket(message_bus, spheros):
    asyncio.run(websocket_receiver(message_bus, spheros))

def run_websocket_sender(outgoing_queue):
    asyncio.run(websocket_sender(outgoing_queue))

if __name__ == "__main__":
    with multiprocessing.Manager() as manager:
        spheros = [
            {"id": "SB-2E86", "color": "#0000FF"},
            {"id": "SB-4844", "color": "#FF0000"},
            {"id": "SB-7104", "color": "#008000"},
            {"id": "SB-D8B2", "color": "#FFFF00"},
        ]

        message_bus = manager.dict({sphero["id"]: manager.list() for sphero in spheros})
        outgoing_queue = manager.Queue()

        websocket_process = multiprocessing.Process(target=run_websocket, args=(message_bus, spheros))
        websocket_sender_process = multiprocessing.Process(target=run_websocket_sender, args=(outgoing_queue,))

        subscriber_processes = [
            multiprocessing.Process(target=run_sphero, args=(sphero["id"], sphero["color"], message_bus, outgoing_queue, True))
            for sphero in spheros
        ]

        websocket_process.start()
        websocket_sender_process.start()

        for process in subscriber_processes:
            process.start()

        logging.info("Main: All processes started.")

        websocket_process.join()
        websocket_sender_process.join()

        for process in subscriber_processes:
            process.join()

        logging.info("Main: All processes terminated.")
