# -*- coding:utf8 -*-

from django import template
from django.contrib.auth.models import User, Group
from django.shortcuts import get_object_or_404
from deploy.models import SaltGroup

register = template.Library()

@register.filter(name='group_minions')
def minions(value):
    '''
    分组列表中显示所有主机
    '''

    try:
        group_minions = value.minions.all()
        return group_minions
    except:
        return ''

@register.filter(name='group_users')
def all_users(group):
    '''
    分组列表中显示所有主机
    '''

    try:
        all_users = group.user_set.all()
        return all_users
    except:
        return ''

@register.filter(name='user_groups')
def all_user_groups(pk):
    '''
    用户所属组
    '''

    try:
        user_group = [i.name for i in Group.objects.filter(user=pk)]
        return user_group
    except:
        return ''

@register.filter(name='is_super')
def user_is_super(pk):
    '''
    是否为超级用户
    '''
    if pk:
        return User.objects.get(pk=pk).is_superuser
    else:
        return False
