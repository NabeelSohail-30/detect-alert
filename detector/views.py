# detector/views.py
from django.shortcuts import render, redirect, get_object_or_404
from .forms import VideoUploadForm
from .models import UploadedVideo, Detection
from ultralytics import YOLO
import cv2
import time

from django.shortcuts import render, redirect
from .forms import VideoUploadForm
import threading
import cv2
import time
import os
from ultralytics import YOLO
import firebase_admin
from firebase_admin import credentials, db
from django.conf import settings

from collections import deque

# set model paths
crowd_model = YOLO("models/crowd.pt")
fire_model = YOLO("models/fire.pt")
gun_model = YOLO("models/gun.pt")

# init Firebase
cred_path = os.path.join(settings.BASE_DIR, 'cred.json')
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://aegis-1f952-default-rtdb.firebaseio.com'
})

def home(request):
    return render(request, 'home.html')

def dashboard(request):
    return render(request, 'dashboard.html')


def insights(request):
    return render(request, 'insights.html')


def upload_video(request):
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save()
            threading.Thread(target=process_video, args=(
                video.video_file.path, video.id)).start()
            return redirect('dashboard')
    else:
        form = VideoUploadForm()
    return render(request, 'upload.html', {'form': form})


crowd_model = YOLO("models/crowd.pt")
fire_model = YOLO("models/fire.pt")
gun_model = YOLO("models/gun.pt")

CONFIDENCE_THRESHOLD = 0.65
CROWD_CONFIDENCE = 0.5
FRAME_THRESHOLD = 3


def process_video(video_path, video_id):
    from .models import UploadedVideo
    video = UploadedVideo.objects.get(id=video_id)
    video_title = os.path.basename(video.video_file.name)

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame = 0

    while True:
        ret, frame_img = cap.read()
        if not ret:
            break

        for label, model in (("Crowd", crowd_model), ("Fire", fire_model), ("Gun", gun_model)):
            res = model(frame_img, verbose=False)[0]
            for conf in res.boxes.conf:
                if float(conf) > 0.75:
                    ts_epoch = int(time.time())
                    timestamp = round(frame / fps, 2)

                    alert_data = {
                        'label': label,
                        'confidence': round(float(conf) * 100, 2),
                        'timestamp': timestamp,
                        'video_id': video_id,
                        'video_title': video_title,
                        'type': 'uploaded'
                    }

                    db.reference(
                        f'alerts/{video_id}/{ts_epoch}').set(alert_data)
                    break

        frame += 1
        time.sleep(1 / fps)

    cap.release()


# def process_video(video_path, video_id):
#     cap = cv2.VideoCapture(video_path)
#     frame_rate = cap.get(cv2.CAP_PROP_FPS)
#     frame_num = 0

#     # Persistent frame counters
#     crowd_counter = 0
#     fire_counter = 0
#     gun_counter = 0

#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break

#         # Inference
#         crowd_results = crowd_model(frame, verbose=False)
#         fire_results = fire_model(frame, verbose=False)
#         gun_results = gun_model(frame, verbose=False)

#         crowd_boxes = crowd_results[0].boxes
#         fire_boxes = fire_results[0].boxes
#         gun_boxes = gun_results[0].boxes

#         # === CROWD DETECTION ===
#         crowd_count = sum(
#             1 for cls, conf in zip(crowd_boxes.cls, crowd_boxes.conf)
#             if int(cls) == 0 and conf > CROWD_CONFIDENCE
#         )

#         if crowd_count > 3:
#             crowd_counter += 1
#         else:
#             crowd_counter = 0

#         if crowd_counter > FRAME_THRESHOLD:
#             Detection.objects.create(
#                 video_id=video_id,
#                 label='Crowd',
#                 confidence=1.0,  # Not per-object confidence, rather confirmed event
#                 timestamp=frame_num / frame_rate
#             )
#             crowd_counter = 0  # Reset

#         # === FIRE DETECTION ===
#         fire_detected = any(conf > CONFIDENCE_THRESHOLD for conf in fire_boxes.conf)

#         if fire_detected:
#             fire_counter += 1
#         else:
#             fire_counter = 0

#         if fire_counter > FRAME_THRESHOLD:
#             max_conf = max(conf for conf in fire_boxes.conf if conf > CONFIDENCE_THRESHOLD)
#             Detection.objects.create(
#                 video_id=video_id,
#                 label='Fire',
#                 confidence=float(max_conf),
#                 timestamp=frame_num / frame_rate
#             )
#             fire_counter = 0

#         # === GUN DETECTION ===
#         gun_detected = any(conf > CONFIDENCE_THRESHOLD for conf in gun_boxes.conf)

#         if gun_detected:
#             gun_counter += 1
#         else:
#             gun_counter = 0

#         if gun_counter > FRAME_THRESHOLD:
#             max_conf = max(conf for conf in gun_boxes.conf if conf > CONFIDENCE_THRESHOLD)
#             Detection.objects.create(
#                 video_id=video_id,
#                 label='Gun',
#                 confidence=float(max_conf),
#                 timestamp=frame_num / frame_rate
#             )
#             gun_counter = 0

#         frame_num += 1

#     cap.release()


from django.http import StreamingHttpResponse
from django.shortcuts import render
import cv2

# camera = cv2.VideoCapture(0)

def gen_frames():  
    cap = cv2.VideoCapture("/dev/video2")
    if not cap.isOpened():
        print("Failed to open webcam")
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    last_detection_time = time.time()
    detection_interval = 1
    video_title = "Webcam Feed"
    video_id = "live_feed"

    while True:
        success, frame = cap.read()
        if not success:
            break

        current_time = time.time()
        if current_time - last_detection_time >= detection_interval:
            for label, model in (("Crowd", crowd_model), ("Fire", fire_model), ("Gun", gun_model)):
                res = model(frame, verbose=False)[0]
                for conf in res.boxes.conf:
                    if float(conf) > 0.85:
                        ts_epoch = int(time.time())

                        alert_data = {
                            'label': label,
                            'confidence': round(float(conf) * 100, 2),
                            'timestamp': round(current_time, 2),
                            'video_id': video_id,
                            'video_title': video_title,
                            'type': 'live'
                        }

                        db.reference(f'alerts/{video_id}/{ts_epoch}').set(alert_data)
                        break  # Alert once per frame per label

            last_detection_time = current_time

        # Stream frame to browser
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()


# # Confidence thresholds per label
# LABEL_THRESHOLDS = {
#     "Crowd": 0.60,
#     "Fire": 0.80,
#     "Gun": 0.75
# }

# # Frame thresholds (consecutive positive detections required per label)
# LABEL_FRAME_THRESHOLDS = {
#     "Crowd": 10,
#     "Fire": 5,
#     "Gun": 5
# }

# # Deques for smoothing (individual length per label)
# detection_deques = {
#     "Crowd": deque(maxlen=LABEL_FRAME_THRESHOLDS["Crowd"]),
#     "Fire": deque(maxlen=LABEL_FRAME_THRESHOLDS["Fire"]),
#     "Gun": deque(maxlen=LABEL_FRAME_THRESHOLDS["Gun"]),
# }

# # Last alert timestamps
# last_alert_time = {"Crowd": 0, "Fire": 0, "Gun": 0}
# ALERT_COOLDOWN = 3  # seconds

# def gen_frames():
#     cap = cv2.VideoCapture("/dev/video0")
#     if not cap.isOpened():
#         print("Failed to open webcam")
#         return

#     fps = cap.get(cv2.CAP_PROP_FPS) or 24
#     last_detection_time = time.time()
#     detection_interval = 1  # seconds

#     video_title = "Webcam Feed"
#     video_id = "live_feed"

#     while True:
#         success, frame = cap.read()
#         if not success:
#             break

#         current_time = time.time()

#         if current_time - last_detection_time >= detection_interval:
#             for label, model in (
#                 ("Crowd", crowd_model),
#                 ("Fire", fire_model),
#                 ("Gun", gun_model)
#             ):
#                 result = model(frame, verbose=False)[0]
#                 confs = result.boxes.conf.tolist() if result.boxes.conf is not None else []

#                 threshold = LABEL_THRESHOLDS[label]
#                 frame_threshold = LABEL_FRAME_THRESHOLDS[label]
#                 detections = detection_deques[label]

#                 # Check if any box meets the confidence threshold
#                 detected = any(float(c) > threshold for c in confs)
#                 detections.append(detected)

#                 print(f"{label} detected: {detected}, confs: {confs}")

#                 # Trigger alert if detection has been true for required consecutive frames
#                 if len(detections) == frame_threshold and all(detections):
#                     ts_epoch = int(time.time())
#                     alert_data = {
#                         'label': label,
#                         'confidence': round(max(confs) * 100, 2) if confs else 0,
#                         'timestamp': round(current_time, 2),
#                         'video_id': video_id,
#                         'video_title': video_title,
#                         'type': 'live'
#                     }
#                     db.reference(f'alerts/{video_id}/{ts_epoch}').set(alert_data)
#                     detections.clear()  # Reset after alert

#             last_detection_time = current_time

#         # Encode and stream frame
#         _, buffer = cv2.imencode('.jpg', frame)
#         frame_bytes = buffer.tobytes()
#         yield (b'--frame\r\n'
#                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

#     cap.release()

    
    
def live_feed(request):
    return StreamingHttpResponse(gen_frames(), content_type='multipart/x-mixed-replace; boundary=frame')

def live_page(request):
    return render(request, 'live.html')

live_detection_thread = None
stop_event = threading.Event()

def start_live_detection(request):
    global live_detection_thread, stop_event
    if request.method == 'POST':
        if live_detection_thread is None or not live_detection_thread.is_alive():
            stop_event.clear()
            live_detection_thread = threading.Thread(target=run_live_detection)
            live_detection_thread.start()
    return redirect('detector:live_page')


def stop_live_detection(request):
    global stop_event
    if request.method == 'POST':
        stop_event.set()
    return redirect('detector:live_page')


def run_live_detection():
    cap = cv2.VideoCapture(0)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    frame_num = 0

    while not stop_event.is_set():
        ret, frame_img = cap.read()
        if not ret:
            break

        for label, model in (("Crowd", crowd_model), ("Fire", fire_model), ("Gun", gun_model)):
            res = model(frame_img, verbose=False)[0]
            for conf in res.boxes.conf:
                if float(conf) > 0.75:
                    ts_epoch = int(time.time())
                    alert_data = {
                        'label': label,
                        'confidence': round(float(conf) * 100, 2),
                        'timestamp': round(time.time(), 2),
                        'video_id': "live_feed",
                        'video_title': "Webcam Feed",
                        'type': 'live'
                    }
                    db.reference(f'alerts/live_feed/{ts_epoch}').set(alert_data)
                    break

        frame_num += 1
        time.sleep(1 / fps)

    cap.release()
