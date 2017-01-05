# -*- coding: utf8 -*-
from django import forms
from django.contrib.auth.models import User, Group
from .models import *

class CommandForm(forms.ModelForm):
    class Meta:
        model = UserCommand
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control','placeholder':'填写别名'}),
            'command': forms.TextInput(attrs={'class': 'tags form-control','id':'tags_add'}),
        }

class DirectoryForm(forms.ModelForm):
    class Meta:
        model = UserDirectory
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control','placeholder':'填写别名'}),
            'directory': forms.TextInput(attrs={'class': 'tags form-control','id':'tags_add'}),
        }
