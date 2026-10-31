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
import tkinter as tk
from tkinter import filedialog

# ==========================
# BLYNK UPDATE
# ==========================
def update_data_to_blynk(value):
    url = f"https://blynk.cloud/external/api/update?token=Sch227Qesr7E7Q0KclrqmPvpAxiKP-U7&V13={value}"
    try:
        requests.get(url)
        print("📡 Blynk updated")
    except Exception as e:
        print("⚠️ Blynk Error:", e)

# ==========================
# YOLO SETUP
# ==========================
net = cv2.dnn.readNet("yolov3.weights", "yolov3.cfg")
with open("coco.names", "r") as f:
    classes = [line.strip() for line in f.readlines()]

layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]

# ==========================
# SOUND MODEL SETUP
# ==========================
MODEL_FILE = "ambulance_sound.h5"
SAMPLE_RATE = 22050
DURATION = 2.5
MEL_N_MELS = 128
DESIRED_LENGTH = 500

labels = ['ambulance', 'firetruck', 'traffic']
encoder = LabelEncoder()
encoder.fit(labels)

model = tf.keras.models.load_model(MODEL_FILE)

ambulance_visual = False
ambulance_sound = False
is_listening = False

# ==========================
# MEL EXTRACTION
# ==========================
def extract_mel(audio):
    mel = librosa.feature.melspectrogram(y=audio, sr=SAMPLE_RATE, n_mels=MEL_N_MELS)
    mel = librosa.power_to_db(mel, ref=np.max)

    if mel.shape[1] < DESIRED_LENGTH:
        mel = np.pad(mel, ((0,0),(0,DESIRED_LENGTH-mel.shape[1])))
    else:
        mel = mel[:, :DESIRED_LENGTH]

    return mel.reshape(1, MEL_N_MELS, DESIRED_LENGTH, 1)

# ==========================
# CENTRAL DECISION FUNCTION
# ==========================
def check_and_update_signal():
    if ambulance_visual and ambulance_sound:
        print("🟢 GREEN LIGHT – Ambulance detected (Visual + Audio)")
        update_data_to_blynk(4)
    else:
        print("🔴 RED LIGHT – Conditions not satisfied")

# ==========================
# MICROPHONE DETECTION
# ==========================
def listen_microphone():
    global ambulance_sound, is_listening
    print("🎙 Microphone listening started...")

    audio = sd.rec(int(DURATION*SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()
    audio = audio.flatten()
    audio = nr.reduce_noise(y=audio, sr=SAMPLE_RATE)

    mel = extract_mel(audio)
    pred = model.predict(mel, verbose=0)
    idx = np.argmax(pred)
    label = encoder.inverse_transform([idx])[0]
    conf = np.max(pred)*100

    ambulance_sound = (label == "ambulance" and conf > 70)
    print(f"[MIC] {label} ({conf:.1f}%)")

    check_and_update_signal()

# ==========================
# GUI FILE PICKER
# ==========================
def choose_audio_file():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select Audio File",
        filetypes=[("Audio Files", "*.wav *.mp3 *.flac")]
    )
    root.destroy()
    return file_path

def detect_audio_file():
    global ambulance_sound
    path = choose_audio_file()
    if not path:
        print("❌ No file selected")
        return

    audio, sr = librosa.load(path, sr=SAMPLE_RATE)
    audio = nr.reduce_noise(y=audio, sr=sr)
    mel = extract_mel(audio)

    pred = model.predict(mel, verbose=0)
    idx = np.argmax(pred)
    label = encoder.inverse_transform([idx])[0]
    conf = np.max(pred)*100

    ambulance_sound = (label == "ambulance" and conf > 70)
    print(f"[FILE] {label} ({conf:.1f}%)")

    check_and_update_signal()

# ==========================
# VISUAL DETECTION
# ==========================
def run_detection(frame):
    global ambulance_visual
    h, w, _ = frame.shape
    blob = cv2.dnn.blobFromImage(frame, 1/255, (416,416), swapRB=True)
    net.setInput(blob)
    outs = net.forward(output_layers)

    ambulance_visual = False

    for out in outs:
        for det in out:
            scores = det[5:]
            cid = np.argmax(scores)
            conf = scores[cid]

            if conf > 0.5 and classes[cid] in ["truck","bus"]:
                cx, cy = int(det[0]*w), int(det[1]*h)
                bw, bh = int(det[2]*w), int(det[3]*h)
                x, y = int(cx-bw/2), int(cy-bh/2)

                roi = frame[max(0,y):y+bh, max(0,x):x+bw]
                if roi.size == 0:
                    continue

                hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                red = cv2.inRange(hsv,(0,120,70),(10,255,255)) + cv2.inRange(hsv,(170,120,70),(180,255,255))
                white = cv2.inRange(hsv,(0,0,200),(180,30,255))

                if cv2.countNonZero(red+white) > 500:
                    ambulance_visual = True
                    label = "🚑 AMBULANCE"
                    color = (0,0,255)
                else:
                    label = classes[cid]
                    color = (0,255,0)

                cv2.rectangle(frame,(x,y),(x+bw,y+bh),color,2)
                cv2.putText(frame,label,(x,y-10),cv2.FONT_HERSHEY_SIMPLEX,0.7,color,2)

    cv2.imshow("Detection", frame)
    cv2.waitKey(1)
    return ambulance_visual

# ==========================
# MAIN LOOP
# ==========================
cap = cv2.VideoCapture(0)
print("SPACE = Visual Detect | Q = Quit")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.resize(frame,(640,480))
    cv2.imshow("Webcam", frame)
    key = cv2.waitKey(1) & 0xFF

    if key == 32:  # SPACE → Visual Detection
        if run_detection(frame.copy()):
            print("✅ Visual detection positive.")
            print("Choose audio detection mode:")
            print("1 → Microphone")
            print("2 → Audio File")

            choice = input("Enter 1 or 2: ").strip()
            if choice == "1":
                listen_microphone()
            elif choice == "2":
                detect_audio_file()
            else:
                print("❌ Invalid option")

    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
