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
                if float(conf) > 0.7:
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
