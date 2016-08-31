#coding:utf8

from django.shortcuts import render
from django.contrib import auth
# Create your views here.
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required

from userperm.views import UserIP
from userperm.models import Message

from .form import LoginForm

@login_required
def index(request):
    return render(request, 'soms_help.html', {})

def login(request):
    if request.method == "POST":
        if request.POST.has_key('login'):
            up = LoginForm(request.POST)
            if up.is_valid():
                username = up.cleaned_data['username']
                password = up.cleaned_data['password']
                print username,password
                user = auth.authenticate(username=username,password=password)
                if user and user.is_active:
                    auth.login(request, user)
                    Message.objects.create(type=u'用户登录', user=request.user, action=u'用户登录', action_ip=UserIP(request),content='用户登录 %s'%request.user)
                    return HttpResponseRedirect('/')
    else:
        up = LoginForm()
    return render(request, 'registration/login.html', {'up':up,'title':'用户登录'})

@login_required
def logout(request):
    Message.objects.create(type=u'用户退出', user=request.user, action=u'用户退出', action_ip=UserIP(request),content='用户退出 %s'%request.user)
    auth.logout(request)
    return HttpResponseRedirect('/')

