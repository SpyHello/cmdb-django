# -*- coding: utf8 -*-

from django import template
from deploy.models import *

register = template.Library()

def show_minions():
    '''
    远程命令、模块部署及文件上传中多项显示主机列表
    '''

    tgt_list = SaltHost.objects.filter(alive=True).filter(status=True)
    return {'tgt_list':tgt_list}

register.inclusion_tag('minions.html')(show_minions)


def show_select_minions():
    '''
    文件回滚中单项显示主机列表
    '''

    tgt_list = SaltHost.objects.filter(alive=True).filter(status=True)
    return {'tgt_list':tgt_list}

register.inclusion_tag('select_minions.html')(show_select_minions)


def show_groups():
    '''
    远程命令、模块部署及文件管理中显示所有分组
    '''

    group_list = SaltGroup.objects.all()
    return {'group_list':group_list}

register.inclusion_tag('groups.html')(show_groups)


def show_modules():
    '''
    模块部署中显示所有模块
    '''

    module_list = ModuleUpload.objects.all()
    return {'module_list':module_list}

register.inclusion_tag('modules.html')(show_modules)


def show_str(value):
    '''
    分割权限控制中远程命令、远程目录列表
    '''

    str_list = value.split(',')
    return {'str_list':str_list}

register.inclusion_tag('strtolist.html')(show_str)


