# detector/views.py
from django.shortcuts import render, redirect, get_object_or_404
from .forms import VideoUploadForm
from .models import UploadedVideo, Detection
from ultralytics import YOLO
import cv2
import time

# Load models (adjust paths as needed)
crowd_model = YOLO("models/crowd.pt")
fire_model = YOLO("models/fire.pt")
gun_model = YOLO("models/gun.pt")

from threading import Thread

def upload_video(request):
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save()

            # Run detection in background
            Thread(target=process_video_real_time, args=(video.video_file.path, video.id)).start()

            return redirect('results_live', video_id=video.id)
    else:
        form = VideoUploadForm()
    return render(request, 'upload.html', {'form': form})

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def process_video_real_time(video_path, video_id):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_num = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = {
            'Crowd': crowd_model(frame, verbose=False)[0],
            'Fire': fire_model(frame, verbose=False)[0],
            'Gun': gun_model(frame, verbose=False)[0]
        }

        for label, result in results.items():
            if result.boxes:
                for conf in result.boxes.conf:
                    if float(conf) > 0.8:
                        timestamp = round(frame_num / fps, 2)
                        alert = {
                            'label': label,
                            'confidence': round(float(conf) * 100, 2),
                            'timestamp': timestamp,
                        }

                        # Send alert to frontend
                        channel_layer = get_channel_layer()
                        async_to_sync(channel_layer.group_send)(
                            f"video_{video_id}",
                            {
                                'type': 'send.alert',
                                'message': alert
                            }
                        )
                        break

        frame_num += 1
        time.sleep(1 / fps)

    cap.release()


def video_results_live(request, video_id):
    video = get_object_or_404(UploadedVideo, id=video_id)
    return render(request, 'results_live.html', {'video': video})


def video_results(request, video_id):
    video = get_object_or_404(UploadedVideo, id=video_id)
    detections = video.detections.all().order_by('timestamp')

    for d in detections:
        d.percentage = round(d.confidence * 100, 2)

    return render(request, 'results.html', {'video': video, 'detections': detections})


CONFIDENCE_THRESHOLD = 0.65
CROWD_CONFIDENCE = 0.5
FRAME_THRESHOLD = 3

def process_video(video_path, video_id):
    cap = cv2.VideoCapture(video_path)
    frame_rate = cap.get(cv2.CAP_PROP_FPS)
    frame_num = 0

    # Persistent frame counters
    crowd_counter = 0
    fire_counter = 0
    gun_counter = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Inference
        crowd_results = crowd_model(frame, verbose=False)
        fire_results = fire_model(frame, verbose=False)
        gun_results = gun_model(frame, verbose=False)

        crowd_boxes = crowd_results[0].boxes
        fire_boxes = fire_results[0].boxes
        gun_boxes = gun_results[0].boxes

        # === CROWD DETECTION ===
        crowd_count = sum(
            1 for cls, conf in zip(crowd_boxes.cls, crowd_boxes.conf)
            if int(cls) == 0 and conf > CROWD_CONFIDENCE
        )

        if crowd_count > 3:
            crowd_counter += 1
        else:
            crowd_counter = 0

        if crowd_counter > FRAME_THRESHOLD:
            Detection.objects.create(
                video_id=video_id,
                label='Crowd',
                confidence=1.0,  # Not per-object confidence, rather confirmed event
                timestamp=frame_num / frame_rate
            )
            crowd_counter = 0  # Reset

        # === FIRE DETECTION ===
        fire_detected = any(conf > CONFIDENCE_THRESHOLD for conf in fire_boxes.conf)

        if fire_detected:
            fire_counter += 1
        else:
            fire_counter = 0

        if fire_counter > FRAME_THRESHOLD:
            max_conf = max(conf for conf in fire_boxes.conf if conf > CONFIDENCE_THRESHOLD)
            Detection.objects.create(
                video_id=video_id,
                label='Fire',
                confidence=float(max_conf),
                timestamp=frame_num / frame_rate
            )
            fire_counter = 0

        # === GUN DETECTION ===
        gun_detected = any(conf > CONFIDENCE_THRESHOLD for conf in gun_boxes.conf)

        if gun_detected:
            gun_counter += 1
        else:
            gun_counter = 0

        if gun_counter > FRAME_THRESHOLD:
            max_conf = max(conf for conf in gun_boxes.conf if conf > CONFIDENCE_THRESHOLD)
            Detection.objects.create(
                video_id=video_id,
                label='Gun',
                confidence=float(max_conf),
                timestamp=frame_num / frame_rate
            )
            gun_counter = 0

        frame_num += 1

    cap.release()