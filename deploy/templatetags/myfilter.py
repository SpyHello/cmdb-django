# -*- coding:utf8 -*-

from django import template
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

