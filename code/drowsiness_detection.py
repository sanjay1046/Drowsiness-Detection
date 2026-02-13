import os
import sys
import time

import cv2
import dlib
import numpy as np
from scipy.spatial import distance as dist
from imutils import face_utils
import requests

THINGSPEAK_WRITE_API_KEY = "9HS155F1EOVXSPVE"  # <-- REPLACE with your API key
THINGSPEAK_URL = "https://api.thingspeak.com/update"
last_upload_time = 0
upload_interval = 15
# EAR function

def eye_aspect_ratio(eye):
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])
    C = dist.euclidean(eye[0], eye[3])
    return (A + B) / (2.0 * C) if C != 0 else 0.0

# MAR function
def mouth_aspect_ratio(mouth):
    A = dist.euclidean(mouth[2], mouth[10])
    B = dist.euclidean(mouth[4], mouth[8])
    C = dist.euclidean(mouth[0], mouth[6])
    return (A + B) / (2.0 * C) if C != 0 else 0.0

# ENED normalized to face width (percent)
def ear_to_nose_distance_percent(shape):
    left_jaw = shape[0]
    right_jaw = shape[16]
    nose = shape[30]
    face_width = dist.euclidean(left_jaw, right_jaw)
    if face_width == 0:
        return 0.0
    ened_px = abs(dist.euclidean(left_jaw, nose) - dist.euclidean(right_jaw, nose))
    return (ened_px / face_width) * 100.0

# Model file
MODEL_PATH = "shape_predictor_68_face_landmarks.dat"
if not os.path.exists(MODEL_PATH):
    print(f"ERROR: landmark model not found at '{MODEL_PATH}'. Download and place it there.")
    sys.exit(1)

detector = dlib.get_frontal_face_detector()
try:
    predictor = dlib.shape_predictor(MODEL_PATH)
except Exception as e:
    print("ERROR: failed to load shape_predictor:", e)
    sys.exit(1)

# Thresholds (tune as needed)
EAR_THRESH = 0.20
MAR_THRESH = 0.60
ENED_THRESH = 8.0    # percent-based threshold
EYE_CLOSE_TIME = 2.0
YAWN_TIME = 3.0
DISTRACT_TIME = 3.0

eye_start = mouth_start = head_start = None

# Open webcam
i=0       # 0- laptop webcam, 1- external webcam
cap = cv2.VideoCapture(i)
if not cap.isOpened():
    print("ERROR: webcam could not be opened. Check camera or try a different index.")
    sys.exit(1)

try:
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("WARNING: failed to read frame from camera. Exiting.")
            break

        # ...existing code...
        # ensure correct dtype and contiguous memory for dlib
        if frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)
        frame = np.ascontiguousarray(frame)

        # convert to RGB (dlib accepts RGB or 8-bit gray) and ensure contiguous uint8
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb = np.ascontiguousarray(rgb)

        faces = detector(rgb, 0)
        if len(faces) > 1:
                cv2.putText(frame, "MULTIPLE FACES DETECTED!", (20, 160),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
        for face in faces:
            shape = predictor(rgb, face)
            shape = face_utils.shape_to_np(shape)
        # ...existing code...

        # single grayscale conversion
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # ensure 8-bit dtype and contiguous memory for dlib
        if gray.dtype != np.uint8:
            gray = gray.astype(np.uint8)
        gray = np.ascontiguousarray(gray)

        faces = detector(gray, 0)
        for face in faces:
            shape = predictor(gray, face)
            shape = face_utils.shape_to_np(shape)

            leftEye = shape[36:42]
            rightEye = shape[42:48]
            mouth = shape[48:68]

            ear = (eye_aspect_ratio(leftEye) + eye_aspect_ratio(rightEye)) / 2.0
            mar = mouth_aspect_ratio(mouth)
            ened = ear_to_nose_distance_percent(shape)

            cv2.putText(frame, f"EAR: {ear:.2f}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
            cv2.putText(frame, f"MAR: {mar:.2f}", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
            cv2.putText(frame, f"ENED%: {ened:.2f}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

            # Drowsiness
            if ear < EAR_THRESH:
                if eye_start is None:
                    eye_start = time.time()
                elif time.time() - eye_start >= EYE_CLOSE_TIME:
                    cv2.putText(frame, "DROWSY!", (150, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 3)
            else:
                eye_start = None

            # Yawning
            if mar >= MAR_THRESH:
                if mouth_start is None:
                    mouth_start = time.time()
                elif time.time() - mouth_start >= YAWN_TIME:
                    cv2.putText(frame, "YAWNING!", (150, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 3)
            else:
                mouth_start = None

            # Distraction (head turned)
            if ened >= ENED_THRESH:
                if head_start is None:
                    head_start = time.time()
                elif time.time() - head_start >= DISTRACT_TIME:
                    cv2.putText(frame, "DISTRACTED!", (150, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,0,0), 3)
            else:
                head_start = None

            for (x, y) in shape:
                cv2.circle(frame, (x, y), 1, (0, 255, 0), -1)

            #Send data to ThingSpeak every 15 seconds
            current_time = time.time()
            if current_time - last_upload_time >= upload_interval:
                try:
                    payload = {
                        'api_key': THINGSPEAK_WRITE_API_KEY,
                        'field1': round(ear, 3),
                        'field2': round(mar, 3),
                        'field3': round(ened, 3)
                    }
                    r = requests.get(THINGSPEAK_URL, params=payload)
                    if r.status_code == 200:
                        print(f"Uploaded to ThingSpeak: EAR={ear:.2f}, MAR={mar:.2f}, ENED={ened:.2f}")
                        last_upload_time = current_time
                    else:
                        print(" ThingSpeak upload failed:", r.text)
                except Exception as e:
                    print(" Error uploading to ThingSpeak:", e)

        cv2.imshow("Driver Drowsiness Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    cap.release()
    cv2.destroyAllWindows()