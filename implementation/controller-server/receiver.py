import asyncio
import json
import multiprocessing
import math
from websockets import connect
from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
from PIL import ImageColor
import time



multiplier = 0.3 # Global variable for adjusting the timing of Sphero movements


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
def process_subscriber(client_id, client_color, message_bus, outgoing_queue, toy):
    

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
                handle_message(client_id, client_color, message_type, message_content, outgoing_queue, toy)
        except Exception as e:
            print(f"{client_id}: Error in subscriber: {e}\n")

# This function connects and calibrates the Spheros
def initialize_sphero(client_id, client_color, message_bus, outgoing_queue,first_run=False, toy=None):
    
    # Keeps trying to connect until a connections is successful
    while toy is None:
        try:
            toy = scanner.find_toy(toy_name=client_id)
        except scanner.ToyNotFoundError as e:
            print(e)
            print(repr(e))
            toy = None
    
    retry = True # Variable for allowing the initialization step to retry if an error occurs

    # Converts the color value from hex to a color object
    rgb = ImageColor.getrgb(client_color)
    client_color = Color(r=rgb[0], g=rgb[1], b=rgb[2])

    # Retries until the initialization completes successfully
    while retry == True:
        try:
            with SpheroEduAPI(toy) as droid:

                retry = False

                # Only calibrates the compass on first startup
                if (first_run == True):
                    droid.calibrate_compass()
                    droid.set_compass_direction(0)
                    
                # sets the main led color
                droid.set_main_led(client_color)

                time.sleep(1) # Probably not needed

        except Exception as e:
            print(e)
            print(repr(e))
            retry = True
    
    # Moves on to processing messages received from websocket
    process_subscriber(client_id, client_color, message_bus, outgoing_queue, toy)
        


# This function tells the Sphero to move and sends feedback
def move(id, client_color, current, target, outgoing_queue, toy):
    # Print the movement path for the Sphero
    print(f"I am moving Sphero {id} at {current} to {target}\n")

    try:
        with SpheroEduAPI(toy) as droid:



            # Turns on the LED for tracking. 
            # The spheros automatically go into sleep mode which is why this is needed
            droid.set_main_led(client_color)

            # Gets the change in x and y coordinates
            deltax = target[0]-current[0]
            deltay = target[1]-current[1]

            # Gets the angle in radians, clockwise
            rad = math.atan2(-deltax, deltay)

            # Converts from radians to degrees
            deg = rad * (180/math.pi)

            # If the angle is negative, add 360 because 270 is west
            if deg < 0:
                deg = deg + 360

            
            # rolls towards the target. Timing needs to be adjusted
            droid.roll(round(deg), 30, math.sqrt(deltax**2+deltay**2)*multiplier)

    except Exception as e:
        print(e)
    
    # Add feedback to the outgoing queue
    send_server = multiprocessing.Process(target=send_message_to_server, args=(outgoing_queue, id, "SpheroFeedback", "Done"))
    send_server.start()
    time.sleep(10)  # Wait to show animation
    send_server.join()


def move_north(id, client_color, time, outgoing_queue, toy):

    try:
        with SpheroEduAPI(toy) as droid:

            # Turns on the LED for tracking. 
            # The spheros automatically go into sleep mode which is why this is needed
            droid.set_main_led(client_color)
            
            # rolls towards the target. Timing needs to be adjusted
            droid.roll(0, 30, time)

    except Exception as e:
        print(e)
    


def move_east(id, client_color, time, outgoing_queue, toy):

    try:
        with SpheroEduAPI(toy) as droid:

            # Turns on the LED for tracking. 
            # The spheros automatically go into sleep mode which is why this is needed
            droid.set_main_led(client_color)
            
            # rolls towards the target. Timing needs to be adjusted
            droid.roll(90, 30, time)

    except Exception as e:
        print(e)
    

def move_south(id, client_color, time, outgoing_queue, toy):

    try:
        with SpheroEduAPI(toy) as droid:

            # Turns on the LED for tracking. 
            # The spheros automatically go into sleep mode which is why this is needed
            droid.set_main_led(client_color)
            
            # rolls towards the target. Timing needs to be adjusted
            droid.roll(180, 30, time)

    except Exception as e:
        print(e)
    

def move_west(id, client_color, time, outgoing_queue, toy):

    try:
        with SpheroEduAPI(toy) as droid:

            # Turns on the LED for tracking. 
            # The spheros automatically go into sleep mode which is why this is needed
            droid.set_main_led(client_color)
            
            # rolls towards the target. Timing needs to be adjusted
            droid.roll(270, 30, time)

    except Exception as e:
        print(e)
    

def set_matrix(id, message, outgoing_queue, toy):
    try:
        with SpheroEduAPI(toy) as droid:

            if message=="X":
                droid.set_heading(0)
                if id == "SB-2E86" or id == "SB-D8B2":
                    droid.set_matrix_character("\\",Color(r=255,g=0,b=0))
                elif id == "SB-4844" or id == "SB-7104":
                    droid.set_matrix_character("/",Color(r=255,g=0,b=0))
                else:
                    print("Droid not found")
            
            elif message=="UpArrow":
                droid.set_heading(0)
                if id == "SB-2E86":
                    droid.set_matrix_line(7,0,0,7,Color(r=0,g=0,b=255))
                    droid.set_matrix_line(7,0,7,7,Color(r=0,g=0,b=255))
                elif id == "SB-4844":
                    droid.set_matrix_line(0,0,7,7,Color(r=0,g=0,b=255))
                    droid.set_matrix_line(0,0,0,7,Color(r=0,g=0,b=255))
                elif id == "SB-7104":
                    droid.set_matrix_line(7,0,7,7,Color(r=0,g=0,b=255))
                elif id == "SB-D8B2":
                    droid.set_matrix_line(0,0,0,7,Color(r=0,g=0,b=255))
                else:
                    print("Droid not found")

            elif message=="RightArrow":
                droid.set_heading(90)
                if id == "SB-4844":
                    droid.set_matrix_line(7,0,0,7,Color(r=0,g=0,b=255))
                    droid.set_matrix_line(7,0,7,7,Color(r=0,g=0,b=255))
                elif id == "SB-D8B2":
                    droid.set_matrix_line(0,0,7,7,Color(r=0,g=0,b=255))
                    droid.set_matrix_line(0,0,0,7,Color(r=0,g=0,b=255))
                elif id == "SB-2E86":
                    droid.set_matrix_line(7,0,7,7,Color(r=0,g=0,b=255))
                elif id == "SB-7104":
                    droid.set_matrix_line(0,0,0,7,Color(r=0,g=0,b=255))
                else:
                    print("Droid not found")

            elif message=="DownArrow":
                droid.set_heading(180)
                if id == "SB-D8B2":
                    droid.set_matrix_line(7,0,0,7,Color(r=0,g=0,b=255))
                    droid.set_matrix_line(7,0,7,7,Color(r=0,g=0,b=255))
                elif id == "SB-7104":
                    droid.set_matrix_line(0,0,7,7,Color(r=0,g=0,b=255))
                    droid.set_matrix_line(0,0,0,7,Color(r=0,g=0,b=255))
                elif id == "SB-4844":
                    droid.set_matrix_line(7,0,7,7,Color(r=0,g=0,b=255))
                elif id == "SB-2E86":
                    droid.set_matrix_line(0,0,0,7,Color(r=0,g=0,b=255))
                else:
                    print("Droid not found")

            
            elif message=="LeftArrow":
                droid.set_heading(270)
                if id == "SB-7104":
                    droid.set_matrix_line(7,0,0,7,Color(r=0,g=0,b=255))
                    droid.set_matrix_line(7,0,7,7,Color(r=0,g=0,b=255))
                elif id == "SB-2E86":
                    droid.set_matrix_line(0,0,7,7,Color(r=0,g=0,b=255))
                    droid.set_matrix_line(0,0,0,7,Color(r=0,g=0,b=255))
                elif id == "SB-28B2":
                    droid.set_matrix_line(7,0,7,7,Color(r=0,g=0,b=255))
                elif id == "SB-4844":
                    droid.set_matrix_line(0,0,0,7,Color(r=0,g=0,b=255))
                else:
                    print("Droid not found")


            '''

            for y in range(8):
                for x in range(8):
                    droid.set_matrix_pixel(x, y, message[y][x])

            '''
    except Exception as e:
        print(e)


    send_server = multiprocessing.Process(target=send_message_to_server, args=(outgoing_queue, id, "SpheroFeedback", "Done"))
    send_server.start()
    time.sleep(10)  # Wait to show animation
    send_server.join()

# This function decides what to do with incoming messages based on their type
def handle_message(id, client_color, message_type, message, outgoing_queue, toy):
    if message_type == "SpheroMovement":
        
        # gets the coordinate data
        current = message["currentLocation"]
        target = message["targetLocation"]
        
        # sends a command to the sphero to move
        move(id, client_color, current, target, outgoing_queue, toy)

    elif message_type == "SpheroMatrix":
        

        set_matrix(id, message, outgoing_queue, toy)

    elif message_type == "MoveNorth":
    
        move_north(id, client_color, message, outgoing_queue, toy)

    elif message_type == "MoveSouth":

        move_south(id, client_color, message, outgoing_queue, toy)

    elif message_type == "MoveWest":

        move_west(id, client_color, message, outgoing_queue, toy)

    elif message_type == "MoveEast":
        move_east(id, client_color, message, outgoing_queue, toy)

    else:
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
            multiprocessing.Process(target=initialize_sphero, args=(sphero["id"], sphero["color"], message_bus, outgoing_queue,True))
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
