# -*- coding: utf8 -*-
from django import forms
from .models import *

class ModuleForm(forms.ModelForm):
    class Meta:
        model = ModuleUpload
        fields = ('name', 'module', 'upload_path', 'remark')
        widgets = {
          'name': forms.TextInput(attrs={'class': 'form-control'}),
          'module': forms.TextInput(attrs={'class': 'form-control'}),
          'upload_path': forms.FileInput(),
          'remark': forms.TextInput(attrs={'class': 'form-control'})
        }

class SaltGroupForm(forms.ModelForm):
    class Meta:
        model = SaltGroup
        fields = ('nickname','minions')
        widgets = {
          'nickname': forms.TextInput(attrs={'class': 'form-control'}),
          'minions': forms.SelectMultiple(attrs={'class': 'form-control'})
        }

class SaltFileForm(forms.ModelForm):
    class Meta:
        model = FileUpload
        fields = ('file_path', 'remote_path', 'remark')
        widgets = {
            'file_path': forms.FileInput(),
            'remote_path': forms.TextInput(attrs={'class': 'form-control'}),
            'remark': forms.TextInput(attrs={'class': 'form-control'})
        }
