import cv2
import numpy as np
from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color
import json

# My Sphero's name
sphero_name = "SB-7104"

class SpheroRobot:
    def __init__(self, sphero_name):
        self.sphero_name = sphero_name
        self.api = None

    def connect(self):
        toy = scanner.find_toy(toy_name=self.sphero_name)
        if toy:
            print(f"Connected to {self.sphero_name}")
            return SpheroEduAPI(toy)
        else:
            print(f"Failed to connect to {self.sphero_name}")
            return None

    def idle(self, api):
        api.set_main_led(Color(0, 0, 0))  # No color

    def spin_reaction(self, api):
        api.set_main_led(Color(0, 255, 0))  # Green LED
        api.spin(360, 1)

    def dance_reaction(self, api):
        api.set_main_led(Color(255, 255, 0))  # Yellow LED
        api.spin(720, 2)

    def stop_reaction(self, api):
        api.set_main_led(Color(255, 0, 0))  # Red LED
        api.roll(0, 0, 0)

    def scared_reaction(self, api):
        api.set_main_led(Color(255, 0, 255))  # Magenta LED
        api.roll(300, 180, 2)  # Roll backward quickly to simulate being scared

class FaceRecognition:
    def __init__(self, model_path, prototxt_path, caffemodel_path, labels_path):
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.recognizer.read(model_path)

        with open(labels_path, 'r') as file:
            self.label_map = json.load(file)

        self.net = cv2.dnn.readNetFromCaffe(prototxt_path, caffemodel_path)

    def recognize_face(self, frame):
        h, w = frame.shape[:2]

        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))
        self.net.setInput(blob)
        detections = self.net.forward()

        person_name = "No face"
        bbox = None

        for i in range(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.5:
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (x, y, x2, y2) = box.astype("int")
                bbox = (x, y, x2, y2)

                face_roi = frame[y:y2, x:x2]
                gray_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)

                try:
                    label, distance = self.recognizer.predict(gray_roi)
                    if distance < 70:
                        person_name = self.label_map.get(str(label), "Unknown")
                    else:
                        person_name = "Unknown"
                except:
                    person_name = "Error"

        return person_name, bbox

# Define the abstract State class
class State:
    def __init__(self, robot):
        self.robot = robot

    def handle(self, api, face_recognition, frame):
        raise NotImplementedError("Each state must implement the 'handle' method")

    def next_state(self, person):
        raise NotImplementedError("Each state must define the next state transitions")

    def get_name(self):
        return self.__class__.__name__

class IdleState(State):
    def handle(self, api, face_recognition, frame):
        self.robot.idle(api)
        person, bbox = face_recognition.recognize_face(frame)
        return person, bbox

    def next_state(self, person):
        if person == "phi":
            return SpinningState(self.robot)
        elif person == "Unknown":  # Only transition to scared if "Unknown" face is detected
            return ScaredState(self.robot)
        return self  # Stay in Idle state if no face or known face is detected

class SpinningState(State):
    def handle(self, api, face_recognition, frame):
        self.robot.spin_reaction(api)
        return "spinning", None

    def next_state(self, person=None):
        if person == "Unknown":
            return ScaredState(self.robot)
        return DancingState(self.robot)

class DancingState(State):
    def handle(self, api, face_recognition, frame):
        self.robot.dance_reaction(api)
        return "dancing", None

    def next_state(self, person=None):
        if person == "Unknown":
            return ScaredState(self.robot)
        return StoppingState(self.robot)

class StoppingState(State):
    def handle(self, api, face_recognition, frame):
        self.robot.stop_reaction(api)
        return "stopping", None

    def next_state(self, person=None):
        if person == "Unknown":
            return ScaredState(self.robot)
        return IdleState(self.robot)

class ScaredState(State):
    def handle(self, api, face_recognition, frame):
        self.robot.scared_reaction(api)
        return "scared", None

    def next_state(self, person):
        if person == "phi":
            return DancingState(self.robot)  # Transition back to dancing if "phi" is detected
        return IdleState(self.robot)

class StateMachine:
    def __init__(self, robot, face_recognition):
        self.robot = robot
        self.face_recognition = face_recognition
        self.current_state = IdleState(self.robot)

    def run(self, api, frame):
        person, bbox = self.current_state.handle(api, self.face_recognition, frame)

        # Print the current state and person detected
        print(f"Current state: {self.current_state.get_name()}, Detected person: {person}")

        # Draw bounding box and display the person detected
        if bbox:
            x, y, x2, y2 = bbox
            cv2.rectangle(frame, (x, y), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"Person: {person}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        # Display the current state on the frame
        state_name = self.current_state.get_name()
        cv2.putText(frame, f"State: {state_name}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        # Transition to the next state and print transition info
        new_state = self.current_state.next_state(person)
        if new_state != self.current_state:
            print(f"Transitioning from {self.current_state.get_name()} to {new_state.get_name()}")
        self.current_state = new_state

def main():
    model_path = 'trained_face_model.yml'
    prototxt_path = 'deploy.prototxt'
    caffemodel_path = 'res10_300x300_ssd_iter_140000.caffemodel'
    labels_path = 'label_map.json'
    
    robot = SpheroRobot(sphero_name)
    
    with robot.connect() as api:
        face_recognition = FaceRecognition(model_path, prototxt_path, caffemodel_path, labels_path)
        state_machine = StateMachine(robot, face_recognition)
    
        cap = cv2.VideoCapture(0)
        while True:
            ret, frame = cap.read()
            if not ret:
                break
        
            state_machine.run(api, frame)
            cv2.imshow("Robot Behavior", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
