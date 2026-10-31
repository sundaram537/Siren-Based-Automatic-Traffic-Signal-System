import cv2
import numpy as np
import threading
import sounddevice as sd
import noisereduce as nr
import librosa
import tensorflow as tf
from sklearn.preprocessing import LabelEncoder
import requests
import time

def update_data_to_blynk(value):
    iot_url = f"https://blynk.cloud/external/api/update?token=3D5AgpyH94GcV2HvA4tuoo26r_tOstj2&V0={value}"
    try:
        response = requests.get(iot_url)
        if response.status_code == 200:
            print("✅ Data sent successfully to Blynk.")
            time.sleep(30)   # ⏳ 30 seconds delay before next update
        else:
            print(f"❌ Failed to send data. Status code: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Error: {e}")

# ==========================
# YOLO setup
# ==========================
net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")
with open("coco.names", "r") as f:
    classes = [line.strip() for line in f.readlines()]
layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

# ==========================
# Sound model setup
# ==========================
MODEL_FILE = "ambulance_sound.h5"
SAMPLE_RATE = 22050
DURATION = 2.5
MEL_N_MELS = 128
DESIRED_LENGTH = 500
classes_sound = ['ambulance', 'firetruck', 'traffic']
encoder = LabelEncoder()
encoder.fit(classes_sound)
model = tf.keras.models.load_model(MODEL_FILE)

# ==========================
# Flags
# ==========================
ambulance_visual = False
ambulance_sound = False
is_listening = False

# ==========================
# Audio feature extraction
# ==========================
def extract_mel_from_audio(audio):
    mel = librosa.feature.melspectrogram(y=audio, sr=SAMPLE_RATE, n_mels=MEL_N_MELS)
    mel = librosa.power_to_db(mel, ref=np.max)
    if mel.shape[1] < DESIRED_LENGTH:
        mel = np.pad(mel, ((0, 0), (0, DESIRED_LENGTH - mel.shape[1])))
    else:
        mel = mel[:, :DESIRED_LENGTH]
    mel = mel.reshape(1, MEL_N_MELS, DESIRED_LENGTH, 1)
    return mel

# ==========================
# Microphone listener
# ==========================
def listen_microphone():
    global ambulance_sound, is_listening
    print("🎙 Starting microphone for ambulance siren detection...")
    while is_listening:
        try:
            audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
            sd.wait()
            audio = audio.flatten()
            reduced = nr.reduce_noise(y=audio, sr=SAMPLE_RATE)
            mel = extract_mel_from_audio(reduced)
            pred = model.predict(mel, verbose=0)
            idx = np.argmax(pred)
            label = encoder.inverse_transform([idx])[0]
            confidence = np.max(pred) * 100
            if label == "ambulance" and confidence > 70:
                ambulance_sound = True
            else:
                ambulance_sound = False
            print(f"[Sound] {label} ({confidence:.1f}%)")

            # Signal update
            if ambulance_sound:
                print("🟢 GREEN LIGHT - Ambulance detected visually & via siren!")
                update_data_to_blynk(1)
            else:
                print("🔴 RED LIGHT - Ambulance siren not detected")
        except Exception as e:
            print("Microphone error:", e)
        time.sleep(0.1)

# ==========================
# Run detection on captured frame
# ==========================
def run_detection(frame):
    global ambulance_visual
    height, width, _ = frame.shape
    blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416,416), swapRB=True, crop=False)
    net.setInput(blob)
    outs = net.forward(output_layers)

    boxes, confidences, class_ids = [], [], []
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.5 and classes[class_id] in ["truck", "bus"]:
                cx, cy = int(detection[0]*width), int(detection[1]*height)
                w, h = int(detection[2]*width), int(detection[3]*height)
                x, y = int(cx - w/2), int(cy - h/2)
                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
    ambulance_visual = False

    if len(indexes) > 0:
        for i in indexes.flatten():
            x, y, w, h = boxes[i]
            # Clip coordinates
            x = max(0, x)
            y = max(0, y)
            w = min(w, frame.shape[1]-x)
            h = min(h, frame.shape[0]-y)
            vehicle = frame[y:y+h, x:x+w]
            if vehicle.size == 0:
                continue
            hsv = cv2.cvtColor(vehicle, cv2.COLOR_BGR2HSV)
            # Red + White mask
            lower_red1, upper_red1 = np.array([0,120,70]), np.array([10,255,255])
            lower_red2, upper_red2 = np.array([170,120,70]), np.array([180,255,255])
            mask_red = cv2.inRange(hsv, lower_red1, upper_red1) + cv2.inRange(hsv, lower_red2, upper_red2)
            lower_white, upper_white = np.array([0,0,200]), np.array([180,30,255])
            mask_white = cv2.inRange(hsv, lower_white, upper_white)
            mask = mask_red + mask_white

            if cv2.countNonZero(mask) > 500:
                ambulance_visual = True
                color = (0,0,255)
                label = "🚑 AMBULANCE"
            else:
                label = classes[class_ids[i]]
                color = (0,255,0)
            cv2.rectangle(frame, (x,y), (x+w, y+h), color, 2)
            cv2.putText(frame, label, (x,y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    # Show frame
    if ambulance_visual:
        cv2.putText(frame, "🚨 AMBULANCE DETECTED", (50,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 3)
        print("🚑 Ambulance detected visually!")
    else:
        cv2.putText(frame, "No Ambulance", (50,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
        print("❌ No ambulance detected visually")
    cv2.imshow("Captured Detection", frame)
    cv2.waitKey(1)

    return ambulance_visual

# ==========================
# Webcam capture first
# ==========================
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Cannot open webcam")
    exit()

print("📷 Press SPACE to capture image for ambulance detection. Press Q to quit webcam.")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame = cv2.resize(frame, (640,480))
    cv2.imshow("Webcam Feed", frame)
    key = cv2.waitKey(1) & 0xFF

    if key == 32:  # SPACE pressed
        captured = frame.copy()
        if run_detection(captured):
            # If ambulance detected visually, start microphone thread
            is_listening = True
            threading.Thread(target=listen_microphone, daemon=True).start()
            print("✅ Visual detection positive. Listening for ambulance siren now...")
        else:
            print("❌ No ambulance detected visually. Microphone will not start.")
    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
