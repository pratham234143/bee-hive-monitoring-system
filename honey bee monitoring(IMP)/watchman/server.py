from flask import Flask, request, send_from_directory
import os
import datetime
import cv2
import numpy as np
import requests
from ultralytics import YOLO

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
DETECTION_FOLDER = 'detections'
MODEL_PATH = 'yolov8x.pt'

# BLYNK CONFIGURATION - REPLACE WITH YOUR DETAILS
BLYNK_AUTH_TOKEN = "NVqVU82XKWW52hAzFg1x_r2V_2MWM7cS"  # Paste your Blynk Auth Token here
BLYNK_SERVER = "https://blynk.cloud" # Or your regional server like https://ny3.blynk.cloud
SERVER_IP = "10.149.116.30" # YOUR PC IP Address (Must be reachable by phone)
SERVER_PORT = "5000"

# Create directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DETECTION_FOLDER, exist_ok=True)

# Initialize YOLO model
print("Loading YOLOv8x model...")
model = YOLO(MODEL_PATH)
print("Model loaded.")

# Global variable to store previous frame for motion detection
prev_frame = None

# COCO Class IDs for relevant animals
ANIMAL_CLASSES = {
    14: 'bird', 15: 'cat', 16: 'dog', 17: 'horse', 18: 'sheep',
    19: 'cow', 20: 'elephant', 21: 'bear', 22: 'zebra', 23: 'giraffe'
}

def send_blynk_update(pin, value):
    """Update a Virtual Pin value (e.g., Motion Status)"""
    try:
        url = f"{BLYNK_SERVER}/external/api/update?token={BLYNK_AUTH_TOKEN}&{pin}={value}"
        response = requests.get(url)
        if response.status_code == 200:
            print(f"Blynk update {pin}: {value} success")
        else:
            print(f"Blynk update failed: {response.text}")
    except Exception as e:
        print(f"Error sending to Blynk: {e}")

def send_blynk_event(event_name, description):
    """Trigger a Blynk Event (for Push Notifications)"""
    try:
        url = f"{BLYNK_SERVER}/external/api/logEvent?token={BLYNK_AUTH_TOKEN}&code={event_name}&description={description}"
        response = requests.get(url)
        if response.status_code == 200:
            print(f"Blynk event {event_name} triggered")
        else:
            print(f"Blynk event failed: {response.text}")
    except Exception as e:
        print(f"Error triggering Blynk event: {e}")

def update_blynk_image(filename):
    """
    Update Image Gallery Widget (V2) with the new image URL.
    Assumption: Phone is on the same local network as this server.
    """
    try:
        image_url = f"http://{SERVER_IP}:{SERVER_PORT}/detections/{filename}"
        
        # 1. Update the 'urls' property to point to the new image
        url_prop = f"{BLYNK_SERVER}/external/api/update/property?token={BLYNK_AUTH_TOKEN}&pin=V2&urls={image_url}"
        requests.get(url_prop)

        # 2. Update the V2 value to 1 (Index 1) to trigger the widget to show the image
        # Note: BLYNK Datastream V2 must be Integer type!
        url_val = f"{BLYNK_SERVER}/external/api/update?token={BLYNK_AUTH_TOKEN}&V2=1" 
        requests.get(url_val)
        
        print(f"Blynk image updated: {image_url}")
    except Exception as e:
        print(f"Error updating Blynk image: {e}")

def detect_motion(current_frame, previous_frame, threshold=35, min_area=1000):
    if previous_frame is None:
        return False

    gray_curr = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
    gray_prev = cv2.cvtColor(previous_frame, cv2.COLOR_BGR2GRAY)

    gray_curr = cv2.GaussianBlur(gray_curr, (21, 21), 0)
    gray_prev = cv2.GaussianBlur(gray_prev, (21, 21), 0)

    delta_frame = cv2.absdiff(gray_prev, gray_curr)
    thresh = cv2.threshold(delta_frame, threshold, 255, cv2.THRESH_BINARY)[1]
    
    thresh = cv2.dilate(thresh, None, iterations=2)
    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    motion_detected = False
    for contour in contours:
        if cv2.contourArea(contour) > min_area:
            motion_detected = True
            break
            
    return motion_detected

@app.route('/detections/<filename>')
def detection_file(filename):
    return send_from_directory(DETECTION_FOLDER, filename)

@app.route('/upload', methods=['POST'])
def upload_file():
    global prev_frame
    
    if 'imageFile' not in request.files:
        return "No imageFile provided", 400
    
    file = request.files['imageFile']
    if file.filename == '':
        return "No selected file", 400
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"capture_{timestamp}.jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    print(f"[{timestamp}] Image saved: {filename}")
    
    frame = cv2.imread(filepath)
    if frame is None:
        return "Image saved but processing failed", 200

    # 1. Motion Detection
    motion = False
    if prev_frame is not None:
        motion = detect_motion(frame, prev_frame)
        if motion:
            print(f"[{timestamp}] MOTION DETECTED!")
            send_blynk_update("V1", "Motion Detected!") # Update V1 status
        else:
            send_blynk_update("V1", "Clear") # Clear status
    else:
        print(f"[{timestamp}] First frame initialized.")

    prev_frame = frame.copy()

    # 2. Object Detection (Only if motion involved or first run logic)
    if motion:
        print(f"[{timestamp}] Running YOLOv8x inference...")
        results = model(frame, verbose=False)
        
        detections_found = False
        animals_detected = []
        
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                
                if cls_id in ANIMAL_CLASSES and conf > 0.4:
                    animal_name = ANIMAL_CLASSES[cls_id]
                    print(f"[{timestamp}] >> DETECTED: {animal_name} ({conf:.2f})")
                    animals_detected.append(animal_name)
                    detections_found = True
                    
                    # Draw box
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(frame, f"{animal_name} {conf:.2f}", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

        if detections_found:
            # Save annotated image
            det_filename = f"detected_{timestamp}.jpg"
            det_filepath = os.path.join(DETECTION_FOLDER, det_filename)
            cv2.imwrite(det_filepath, frame)
            print(f"[{timestamp}] Detection saved to {det_filename}")
            
            # Send Notification to Blynk
            unique_animals = list(set(animals_detected))
            alert_msg = f"Predator Alert: {', '.join(unique_animals)} detected!"
            send_blynk_event("predator_alert", alert_msg)
            
            # Update Image Gallery in Blynk
            update_blynk_image(det_filename)

    return "Image processed", 200

@app.route('/')
def index():
    return "ESP32-CAM Smart Server is running."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
