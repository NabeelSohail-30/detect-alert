# detector/forms.py
from django import forms
from .models import UploadedVideo

class VideoUploadForm(forms.ModelForm):
    class Meta:
        model = UploadedVideo
        fields = ['title', 'video_file']
