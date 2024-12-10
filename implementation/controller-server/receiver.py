import asyncio
import json
import multiprocessing
from websockets import connect
from spherov2 import scanner
from sphero_subclass import MySpheroEduAPI
from spherov2.types import Color
from PIL import ImageColor
import time
import logging
from sphero_movement import SpheroMovement  # Import the movement class

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
                    while not outgoing_queue.empty():
                        message = outgoing_queue.get_nowait()
                        await ws.send(json.dumps(message))
                        logging.info(f"WebSocket Sender: Sent message: {message}")
                except Exception as e:
                    logging.error(f"WebSocket Sender: Error sending message: {e}")
                    break
                await asyncio.sleep(0.1)
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
    except Exception as e:
        logging.error(f"Error adding message to outgoing queue: {e}")

# This function processes incoming messages for a specific Sphero
def process_subscriber(client_id, client_color, message_bus, outgoing_queue, sphero):
    logging.info(f"{client_id}: Subscribed to message bus.")
    while True:
        try:
            if message_bus[client_id]:
                parsed_message = json.loads(message_bus[client_id].pop(0))
                message_type = parsed_message["messageType"]
                message_content = parsed_message["message"]
                handle_message(client_id, client_color, message_type, message_content, outgoing_queue, sphero)
        except Exception as e:
            logging.error(f"{client_id}: Error in subscriber: {e}")

# This function handles specific messages for the Sphero
def handle_message(id, client_color, message_type, message, outgoing_queue, sphero):
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
    first_run_bool = first_run

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
            with MySpheroEduAPI(toy) as droid:
                if first_run_bool:
                    logging.info(f"{client_id}: Calibrating compass.")
                    droid.calibrate_compass()
                    droid.set_compass_direction(0)
                    send_message_to_server(outgoing_queue, client_id, "SpheroReady", "Ready")
                    first_run_bool = False
                droid.set_main_led(client_color)
                logging.info(f"{client_id}: Initialization complete.")
                sphero = SpheroMovement(droid, client_id, client_color, outgoing_queue)
                process_subscriber(client_id, client_color, message_bus, outgoing_queue, sphero)

        except Exception as e:
            logging.error(f"{client_id}: Failed to initialize or maintain connection to Sphero: {e}")

        finally:
            # Clean up and prepare for retry
            logging.warning(f"{client_id}: Sphero connection closed. Retrying...")
            time.sleep(5)  # Retry delay before attempting to reconnect

# WebSocket processes
def run_websocket(message_bus, spheros):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(websocket_receiver(message_bus, spheros))
    finally:
        loop.close()

def run_websocket_sender(outgoing_queue):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(websocket_sender(outgoing_queue))
    finally:
        loop.close()

if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")

    with multiprocessing.Manager() as manager:
        spheros = [
            {"id": "SB-2E86", "color": "#FF00FF", "ready": False},
            {"id": "SB-4844", "color": "#FF0000", "ready": False},
            {"id": "SB-7104", "color": "#008000", "ready": False},
            {"id": "SB-D8B2", "color": "#00FFFF", "ready": False},
        ]

        message_bus = manager.dict({sphero["id"]: manager.list() for sphero in spheros})
        outgoing_queue = manager.Queue()

        websocket_process = multiprocessing.Process(target=run_websocket, args=(message_bus, spheros))
        websocket_sender_process = multiprocessing.Process(target=run_websocket_sender, args=(outgoing_queue,))

        websocket_process.start()
        websocket_sender_process.start()

        subscriber_processes = []

        for sphero in spheros:
            process = multiprocessing.Process(target=run_sphero, args=(sphero["id"], sphero["color"], message_bus, outgoing_queue, True))
            process.start()
            subscriber_processes.append(process)
            time.sleep(4) 

        logging.info("Main: All processes started.")

        websocket_process.join()
        websocket_sender_process.join()

        for process in subscriber_processes:
            process.join()

        logging.info("Main: All processes terminated.")
