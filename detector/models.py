# detector/models.py
from django.db import models

class UploadedVideo(models.Model):
    title = models.CharField(max_length=255)
    video_file = models.FileField(upload_to='videos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

class Detection(models.Model):
    video = models.ForeignKey(UploadedVideo, on_delete=models.CASCADE, related_name="detections")
    label = models.CharField(max_length=50)
    confidence = models.FloatField()
    timestamp = models.FloatField()
