# -*- coding:utf8 -*-
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, HttpResponse

from django.http import StreamingHttpResponse

from django.contrib.auth.decorators import login_required
from deploy.saltapi import SaltAPI

from soms import settings
from userperm.views import UserIP
from userperm.models import *
from .models import *
from .forms import *
from tar_file import make_tar

try:
    import json
except ImportError:
    import simplejson as json

#import time
import datetime
import shutil
import os
import re
import tarfile, zipfile
# Create your views here.

def RemoteExec(request, fun, group=False):
    '''
    定义远程命令函数
    '''

    danger = []
    for i in UserCommand.objects.filter(name='ENGINEDEV'):
        danger = i.command.split(',')
    if len(danger) == 0:
        danger = ['reboot', 'shutdown']
    check = False
    is_group = False
    ret = ''
    jid = ''
    arg = ''
    if request.method == 'POST':
        if request.is_ajax():
            if request.POST.get('check_type') == 'panel-group':
                grp = request.POST.get('tgt_select')
                tgt_list = SaltGroup.objects.get(nickname=grp).groupname
                expr_form = 'nodegroup'
                is_group = True
            else:
                tgt_select = request.POST.getlist('tgt_select[]')
                if not tgt_select:
                    tgt_list = request.POST.get('tgt_select')
                else:
                    tgt_list = ','.join(tgt_select)
                expr_form = 'list'
            if fun == 'cmd.run':
                arg = request.POST.get('arg')
            else:
                arg = request.POST.get('module_list')
                arg = 'module.user_%s.%s'%(request.user.id,arg)
            sapi = SaltAPI(url=settings.SALT_API['url'],username=settings.SALT_API['user'],password=settings.SALT_API['password'])
            if arg not in danger or request.user.is_superuser:
                try:
                    if fun == 'cmd.run':
                        jid = sapi.remote_execution(tgt_list, fun, arg + ';echo ":::"$?', expr_form)
                        if is_group:
                            s = SaltGroup.objects.get(groupname=tgt_list)
                            s_len = s.minions.all().count()
                        else:
                            s = tgt_list.split(',')
                            s_len = len(s)
                        rst = {}
                        while(len(rst)<s_len):
                            rst = sapi.salt_runner(jid)
                            #time.sleep(1)
                        for k in rst:
                            ret = ret + u'主机：' + k + '\n运行结果：\n%s\n'%rst[k]
                            r = rst[k].split(':::')[-1].strip()
                            if r != '0':
                                ret = ret + '%s 执行失败！\n'%arg + '-'*80 + '\n'
                            else:
                                ret = ret + '%s 执行成功！\n'%arg + '-'*80 + '\n'
    
                    else:
                        jid = sapi.remote_execution(tgt_list, fun, arg, expr_form)
                        rst = sapi.salt_runner(jid)
                        rst = ret['data']
                        rst_all = ''
                        for k in rst:
                            r_str = ''
                            for k1 in rst[k]:
                                if 'cmd_' in k1:
                                    v1 = rst[k][k1]
                                    if v1['result']:
                                        result = u'成功'
                                    else:
                                        result = u'失败'
                                    try:
                                        stderr = v1['changes']['stderr']
                                    except:
                                        stderr = ''
                                    v_str = u'运行结果：' + result + u'\n错误：' + stderr + u'\n内容：' + v1['comment'] + u'\n命令：' + v1['name'] + u'\n开始时间：' + v1['start_time'] + u'\n耗时：' + str(v1['duration']) + '\n'
                                    r_str = u'主机：' + k + '\n' + v_str + '-'*80 + '\n'
                            rst_all = rst_all + r_str
                        ret = rst_all
                except:
                    pass
                if not arg or not tgt_list:
                    ret = u'未选择主机或未输入命令...'
                if ret:
                    ret = ret + '\nJobs NO. %s'%jid
                else:
                    check = True
                    ret = u'命令执行中，请稍候查询结果...\nJobs NO. %s'%jid
            else:
                ret = u'无权限执行此命令！'
    return {'ret':ret, 'arg':arg, 'jid':jid, 'check':check, 'is_group':is_group}

def UploadFile(request, form, group=False):
    '''
    定义文件上传函数
    '''

    danger = []
    check = False
    is_group = False
    rst = ''
    ret = ''
    jid = ''
    fileupload = FileUpload()
    if request.method == 'POST':
        form = SaltFileForm(request.POST, request.FILES, instance=fileupload)
        remote_path = request.POST.get('remote_path')
        for i in UserDirectory.objects.filter(name='ENGINEDEV_PATH'):
            danger = i.directory.split(',')
        if len(danger) == 0:
            danger = ['/etc', '/boot']
        if remote_path not in danger or request.user.is_superuser:
            if form.is_valid and request.is_ajax():
                cur_name = request.FILES['file_path'].name
                if request.POST.get('check_type') == 'panel-group':
                    grp = request.POST.get('tgt_select')
                    tgt_list = SaltGroup.objects.get(nickname=grp).groupname
                    expr_form = 'nodegroup'
                    is_group = True
                    tgt_select = [tgt_list]
                else:
                    tgt_select = request.POST.getlist('tgt_select')
                    tgt_list = ','.join(tgt_select)
                    expr_form = 'list'
                for tgt in tgt_select:
                    fileupload = form.save(commit=False)
                    fileupload.user = request.user
                    fileupload.target = tgt
                    fileupload.file_tag = '%s-%s-%s'%(cur_name,request.user.id,datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
                    fileupload.save()
                # 替换路径为<salt://>形式，详细可查看salt上传文件命令
                local_path = str(fileupload.file_path).replace('salt/fileupload','salt://fileupload')
                remote_path = '%s/%s'%(fileupload.remote_path, cur_name)
                sapi = SaltAPI(url=settings.SALT_API['url'],username=settings.SALT_API['user'],password=settings.SALT_API['password'])
                # 备份远程文件
                ret_bak = sapi.file_bak(tgt_list, 'cp.push', remote_path, expr_form)
                # 上传文件到远程
                ret = sapi.file_copy(tgt_list, 'cp.get_file', local_path, remote_path, expr_form)
                # 分组上传文件时，只需从其中一台salt主机备份文件，备份完成后设置group_forloop为false
                group_forloop = True

                for k in ret:
                    if request.POST.get('check_type') == 'panel-group':
                        bakup_path = './media/salt/filebakup/user_%s/%s'%(request.user.id,tgt_list)
                    else:
                        bakup_path = './media/salt/filebakup/user_%s/%s'%(request.user.id,k)
                    if not os.path.exists('%s%s'%(bakup_path, fileupload.remote_path)):
                        os.makedirs('%s%s'%(bakup_path, fileupload.remote_path))
                    if ret[k]:
                        rst = rst + u'主机：' + k + '\n上传结果：\n' + ret[k] + '\n'
                        if ret_bak[k]:
                            bak_file = '%s%s/%s'%(bakup_path,fileupload.remote_path,fileupload.file_tag)
                            # 替换路径为<salt://>形式，以便文件回滚
                            bak_path = bak_file.replace('./media/salt','salt:/')
                            if request.POST.get('check_type') == 'panel-group' and group_forloop:
                                shutil.copy('/var/cache/salt/master/minions/%s/files/%s' % (k,remote_path), bak_file)
                                try:
                                    FileRollback.objects.get_or_create(user=request.user,target=tgt_list,cur_path=remote_path,bak_path=bak_path,file_tag=fileupload.file_tag,remark=fileupload.remark,is_group=True)
                                except:
                                    print 'not create'
                                group_forloop = False
                            else:
                                try:
                                    shutil.copy('/var/cache/salt/master/minions/%s/files/%s' % (k,remote_path), bak_file)
                                except:
                                    print 'No such file or dirctory'
                                try:
                                    FileRollback.objects.get_or_create(user=request.user,target=k,cur_path=remote_path,bak_path=bak_path,file_tag=fileupload.file_tag,remark=fileupload.remark)
                                except:
                                    print 'not create'

                            rst = rst + u'远程文件%s备份成功...'%remote_path + '\n' + '-'*80 + '\n'

                        else:
                            rst = rst + u'远程文件%s不存在，备份失败...'%remote_path + '\n' + '-'*80 + '\n'
                    else:
                        rst = rst + u'主机：' + k + '\n上传结果：\n失败\n' + '-'*80 + '\n'
        else:
            rst = u'无权限更改此目录'

    return {'ret':rst, 'check':check, 'is_group':is_group}

def AjaxResult(jid,check_type):
    '''
    定义ajax查询结果函数
    '''

    true = True
    sapi = SaltAPI(url=settings.SALT_API['url'],username=settings.SALT_API['user'],password=settings.SALT_API['password'])
    ret = sapi.salt_runner(jid)
    if check_type == 'deploy':
        rst = ret['data']
        rst_all = ''
        for k in rst:
            r_str = ''
            for k1 in rst[k]:
                if 'cmd_' in k1:
                    v1 = rst[k][k1]
                    if v1['result']:
                        result = u'成功'
                    else:
                        result = u'失败'
                    try:
                        stderr = v1['changes']['stderr']
                    except:
                        stderr = ''
                    v_str = u'运行结果：' + result + u'\n错误：' + stderr + u'\n内容：' + v1['comment'] + u'\n命令：' + v1['name'] + u'\n开始时间：' + v1['start_time'] + u'\n耗时：' + str(v1['duration']) + '\n'
                    r_str = u'主机：' + k + '\n' + v_str + '-'*80 + '\n'
            rst_all = rst_all + r_str
    else:
        rst_all = ''
        for k in ret:
            r_str = u'主机：' + k + u'\n运行结果：\n' + ret[k] + '\n' + '-'*80 + '\n'
            rst_all = rst_all + r_str

    try:
        # 记录查询操作日志
        message = get_object_or_404(Message, action=jid)
        m = re.search('\[([^:]*)\]', message.content)
        module = m.groups()[0]
        message.content = '[%s]\n----\n%s'%(module,rst_all)
        message.save()
    except:
        print 'Err'
        pass

    return rst_all

@login_required
def salt_key_list(request):
    '''
    salt主机列表
    '''

    if request.user.is_superuser:
        minions = SaltHost.objects.filter(status=True)
        minions_pre = SaltHost.objects.filter(status=False)
        return render(request, 'salt_key_list.html', {'all_minions':minions,'all_minions_pre':minions_pre})
    else:
        raise Http404

@login_required
def salt_key_import(request):
    '''
    导入salt主机
    '''
    if request.user.is_superuser:
        sapi = SaltAPI(url=settings.SALT_API['url'],username=settings.SALT_API['user'],password=settings.SALT_API['password'])
        minions,minions_pre = sapi.list_all_key()
        alive = False
        ret_alive = sapi.salt_alive('*')
        for node_name in minions:
            try:
                alive = ret_alive[node_name]
                alive = True
            except:
                alive = False
            try:
                SaltHost.objects.create(hostname=node_name,alive=alive,status=True)
            except:
                salthost = SaltHost.objects.get(hostname=node_name)
                now = datetime.datetime.now()
                alive_old = SaltHost.objects.get(hostname=node_name).alive
                if alive != alive_old:
                    salthost.alive_time_last = now
                    salthost.alive = alive
                salthost.alive_time_now = now
                salthost.save()
        for node_name in minions_pre:
            try:
                SaltHost.objects.get_or_create(hostname=node_name,alive=alive,status=False)
            except:
                print 'not create'

        return redirect('key_list')
    else:
        raise Http404

@login_required
def salt_key_manage(request, hostname=None):
    '''
    接受或拒绝salt主机，同时更新数据库
    '''
    if request.user.is_superuser:
        if request.method == 'GET':
            sapi = SaltAPI(url=settings.SALT_API['url'],username=settings.SALT_API['user'],password=settings.SALT_API['password'])
            hostname = request.GET.get('hostname')
            salthost = SaltHost.objects.get(hostname=hostname)
            action = ''
            if request.GET.has_key('add'):
                ret = sapi.accept_key(hostname)
                if ret:
                    salthost.status=True
                    salthost.save()
                    action = u'添加主机'
            if request.GET.has_key('delete'):
                ret = sapi.delete_key(hostname)
                if ret:
                    salthost.status=False
                    salthost.save()
                    action = u'删除主机'
            if request.GET.has_key('flush'):
                ret = sapi.salt_alive(hostname)
                try:
                    alive = ret[hostname]
                    alive = True
                except:
                    alive = False
                salthost.alive=alive
                salthost.save()
                action = u'刷新主机'
            if action:
                    Message.objects.create(type=u'部署管理', user=request.user, action=action, action_ip=UserIP(request),content=u'%s %s'%(action,salthost.hostname))
        return redirect('key_list')
    else:
        raise Http404

@login_required
def salt_group_list(request):
    '''
    salt主机分组列表
    '''

    if request.user.is_superuser:
        groups = SaltGroup.objects.all()
        return render(request, 'salt_group_list.html', {'all_groups': groups})
    else:
        raise Http404

@login_required
def salt_group_manage(request, id=None):    
    '''
    salt主机分组管理，同时更新salt-master配置文件
    '''
    if request.user.is_superuser:
        action = ''
        page_name = ''
        if id:
            group = get_object_or_404(SaltGroup, pk=id)
            action = 'edit'
            page_name = '编辑分组'
        else:
            group = SaltGroup()
            action = 'add'
            page_name = '新增分组'

        if request.method == 'GET':
            if request.GET.has_key('delete'):
                id = request.GET.get('id')
                group = get_object_or_404(SaltGroup, pk=id)
                group.delete()
                Message.objects.create(type=u'部署管理', user=request.user, action=u'删除分组', action_ip=UserIP(request),content='删除分组 %s'%group.nickname)
                with open('./saltconfig/nodegroup.conf','r') as f:
                    with open('./nodegroup', 'w') as g:
                        for line in f.readlines():
                            if group.groupname not in line:
                                g.write(line)
                shutil.move('./nodegroup','./saltconfig/nodegroup.conf')
                return redirect('group_list')

        if request.method == 'POST':
            form = SaltGroupForm(request.POST, instance=group)
            if form.is_valid():
                minions = request.POST.getlist('minions')
                # 前台分组以别名显示，组名不变
                if action == 'add':
                    group = form.save(commit=False)
                    group.groupname = form.cleaned_data['nickname']
                else:
                    try:
                        group.minions.clear()
                    except:
                        pass
                    form.save
                group.save()
                for m in minions:
                    group.minions.add(m)

                Message.objects.create(type=u'部署管理', user=request.user, action=page_name, action_ip=UserIP(request),content='%s %s'%(page_name,group.nickname))

                minions_l = []
                for m in group.minions.values('hostname'):
                    minions_l.append(m['hostname'])
                minions_str = ','.join(minions_l)
                try:
                    with open('./saltconfig/nodegroup.conf','r') as f:
                        with open('./nodegroup', 'w') as g:
                            for line in f.readlines():
                                if group.groupname not in line:
                                    g.write(line)
                            g.write("  %s: 'L@%s'\n"%(group.groupname,minions_str))
                    shutil.move('./nodegroup','./saltconfig/nodegroup.conf')
                except:
                    with open('./saltconfig/nodegroup.conf', 'w') as g:
                        g.write("nodegroups:\n  %s: 'L@%s'\n"%(group.groupname,minions_str))

                import subprocess
                subprocess.Popen('systemctl restart salt-api', shell=True)
                return redirect('group_list')
        else:
            form = SaltGroupForm(instance=group)

        return render(request, 'salt_group_manage.html', {'form':form, 'action':action, 'page_name':page_name})
    else:
        raise Http404

@login_required
def salt_module_list(request):
    '''
    模块列表
    '''
    if request.user.has_perm('deploy.view_moduleupload'):
        modules = ModuleUpload.objects.all()
        return render(request, 'salt_module_list.html', {'modules':modules})
    else:
        raise Http404

@login_required
def salt_module_manage(request, id=None):
    '''
    模块管理
    '''
    ret = ''
    upload_stat = True
    if id:
        module = get_object_or_404(ModuleUpload, pk=id)
        old_path = module.upload_path.path.split('.')
        action = 'edit'
        page_name = '编辑模块'
    else:
        module = ModuleUpload()
        action = 'add'
        page_name = '新增模块'

    if request.method == 'GET':
        if request.GET.has_key('delete'):
            id = request.GET.get('id')
            module = get_object_or_404(ModuleUpload, pk=id)
            module.delete()
            Message.objects.create(type=u'部署管理', user=request.user, action=u'删除模块', action_ip=UserIP(request),content=u'删除模块 %s'%module.name)
            cur_path = module.upload_path.path.split('.')[0]
            try:
                os.remove('%s.sls'%(cur_path))
            except:
                shutil.rmtree(cur_path, ignore_errors=True)
            return redirect('module_list')

    if request.method == 'POST':
        ext_path = './media/salt/module/user_%s'%request.user.id
        form = ModuleForm(request.POST, request.FILES, instance=module)
        if form.is_valid():
            file_exists = request.POST.get('upload_path')
            file_name = form.cleaned_data['upload_path']
            file_ext = str(file_name).split('.')[-1]
            ext = ['bz2','gz','zip','sls']
            if file_ext in ext:
                if action == 'add':
                    module = form.save(commit=False)
                else:
                    form.save
                module.user = request.user
                module.save()

                Message.objects.create(type=u'部署管理', user=request.user, action=page_name, action_ip=UserIP(request),content='%s %s'%(page_name,module.name))

                src = module.upload_path.path

                if file_exists == None:
                    try:
                        os.remove('%s.sls'%old_path[0])
                    except:
                        pass
                    try:
                        if file_ext == 'zip':
                            tar = zipfile.ZipFile(src)
                        else:
                            tar = tarfile.open(src)

                        tar.extractall(path=ext_path)
                        tar.close()
                        ret = u'模块 %s 已上传完成！'%(file_name)
                    except:
                        upload_stat = False
                        ret = u'模块 %s 上传失败，请上传.sls文件或.tar.gz/.tar.bz2/.zip压缩包并确认压缩文件是否损坏！'%(file_name)
                    try:
                        os.remove(src)
                    except:
                        shutil.rmtree(src, ignore_errors=True)
                        pass

                if upload_stat:
                    return redirect('module_list')
                else:
                    return render(request, 'salt_module_manage.html', {'form':form, 'action':action, 'page_name':page_name, 'ret':ret})
            else:
                ret = u'不支持的文件格式，请上传.sls文件或.tar.gz/.tar.bz2/.zip压缩包！'
    else:
        form = ModuleForm(instance=module)
    return render(request, 'salt_module_manage.html', {'form':form, 'action':action, 'page_name':page_name, 'ret':ret})

@login_required
def salt_ajax_result(request):
    '''
    ajax方式查询结果
    '''
    if request.method == 'POST':
        check_type = request.POST.get('type')
        jid = request.POST.get('jid', None)
        if request.is_ajax():
            rst_all = AjaxResult(jid,check_type)

            return HttpResponse(json.dumps(rst_all))

@login_required
def salt_ajax_minions(request):
    '''
    获取不同分组下的主机列表
    '''
    ret = []
    if request.method == 'POST':
        grp = request.POST.get('tgt_select', None)
        tgt_select = SaltGroup.objects.get(nickname=grp).groupname
        if request.is_ajax():
            group = SaltGroup.objects.get(groupname=tgt_select)
            group_minions = group.minions.all()
            for i in group_minions:
                ret.append(i.hostname)

            return HttpResponse(json.dumps(ret))

@login_required
def salt_remote_exec(request):
    '''
    salt远程命令界面
    '''
    return render(request, 'salt_remote_exec.html', {'groups':['panel-single','panel-group']})

@login_required
def salt_ajax_remote_exec(request):
    '''
    salt远程命令执行
    '''
    rst = RemoteExec(request, fun='cmd.run')
    Message.objects.create(type=u'部署管理', user=request.user, action=rst['jid'], action_ip=UserIP(request),content=u'远程管理 [%s]\n %s'%(rst['arg'],rst['ret']))
    return HttpResponse(json.dumps(rst))

@login_required
def salt_module_deploy(request):
    '''
    salt模块部署界面
    '''
    modules = ModuleUpload.objects.all()
    return render(request, 'salt_module_deploy.html', {'modules':modules, 'groups':['panel-single','panel-group']})

@login_required
def salt_ajax_module_deploy(request):
    '''
    salt模块部署
    '''
    rst = RemoteExec(request, fun='state.sls')
    Message.objects.create(type=u'部署管理', user=request.user, action=rst['jid'], action_ip=UserIP(request),content=u'模块部署 [%s]\n %s'%(rst['arg'],rst['ret']))
    return HttpResponse(json.dumps(rst))

@login_required
def salt_file_upload(request):
    '''
    文件上传界面
    '''
    form = SaltFileForm()
    return render(request, 'salt_file_upload.html', {'form':form,'groups':['panel-single','panel-group']})

@login_required
def salt_file_download(request):
    def file_iterator(file_name, chunk_size=512):
        with open(file_name) as f:
            while True:
                c = f.read(chunk_size)
                if c:
                    yield c
                else:
                    break

    sapi = SaltAPI(url=settings.SALT_API['url'],username=settings.SALT_API['user'],password=settings.SALT_API['password'])

    if request.method == 'POST':
        if request.POST.get('type') == 'list':
            rst = RemoteExec(request, fun='cmd.run')
            return HttpResponse(json.dumps(rst['ret']))
        else:
            tgt_list = request.POST.get('tgt_select', None)
            arg = request.POST.get('arg', None)
            jid = sapi.remote_execution(tgt_list, 'cmd.run', 'if [ -d %s ];then echo 0;else echo 1;fi'%arg, 'list')
            rst = sapi.salt_runner(jid)
            if rst[tgt_list] == '0':
                return HttpResponse(json.dumps(arg))
            elif rst[tgt_list] == '1':
                return HttpResponse(json.dumps("download"))
            else:
                print 'Err'
    if request.method == 'GET':
        if request.GET.get('type') == 'download':
            tgt_select = request.GET.get('tgt_select', None)
            arg = request.GET.get('arg', None)
            remote_file = arg
            ret_bak = sapi.file_bak(tgt_select, 'cp.push', remote_file, 'list')
            if tgt_select == 'localhost':
                return render(request,'redirect.html',{})
            remote_path = remote_file.replace(remote_file.split('/')[-1],'')
            dl_path = './media/salt/filedownload/user_%s/%s%s'%(request.user.id,tgt_select,remote_path)
            dl_file = '%s%s'%(dl_path,remote_file.split('/')[-1])
            if not os.path.exists(dl_path):
                os.makedirs(dl_path)
            try:
                shutil.copy('/var/cache/salt/master/minions/%s/files/%s' % (tgt_select,remote_file), dl_file)
                tar_file = make_tar(dl_file,'/tmp')
                dl_filename = 'attachment;filename="{0}"'.format(tar_file.replace('/tmp/','%s%s'%(tgt_select,remote_path)))
                ret = u'主机：%s\n结果：远程文件 %s 下载成功！'%(tgt_select,remote_file)
                Message.objects.create(type=u'文件管理', user=request.user, action=u'文件下载', action_ip=UserIP(request),content=u'下载文件 \n%s'%ret)
                response = StreamingHttpResponse(file_iterator(tar_file))
                response['Content-Type'] = 'application/octet-stream'
                response['Content-Disposition'] = dl_filename

                return response

            except:
                print 'No such file or dirctory'
                ret = u'主机：%s\n结果：远程文件 %s 下载失败，请确认文件是否存在！'%(tgt_select,remote_file)
                Message.objects.create(type=u'文件管理', user=request.user, action=u'文件下载', action_ip=UserIP(request),content=u'下载文件 \n%s'%ret)
                return render(request, 'salt_file_download.html', {'ret':ret})

    return render(request, 'salt_file_download.html', {})

@login_required
def salt_ajax_file_upload(request):
    '''
    执行文件上传
    '''
    form = SaltFileForm()
    ret = UploadFile(request,form=form)
    Message.objects.create(type=u'文件管理', user=request.user, action=u'文件上传', action_ip=UserIP(request),content=u'上传文件 %s'%ret['ret'])
    return HttpResponse(json.dumps(ret['ret']))

@login_required
def salt_file_rollback(request):
    '''
    文件回滚界面
    '''
    form = SaltFileForm()
    return render(request, 'salt_file_rollback.html', {'form':form,'groups':['panel-single','panel-group']})

@login_required
def salt_ajax_file_rollback(request):
    '''
    执行文件回滚
    '''
    true = True
    if request.method == 'POST':
        if request.is_ajax():
            r_list = []
            if request.POST.get('check_type') == 'rollback_file':
                if request.POST.get('get_type') == 'panel-group':
                    grp = request.POST.get('tgt_select')
                    tgt_select = SaltGroup.objects.get(nickname=grp).groupname
                else:
                    tgt_select = request.POST.get('tgt_select')
                rollback_list = FileRollback.objects.filter(target=tgt_select)
                r_list = []
                for r in rollback_list:
                    r_list.append(r.cur_path)
                func = lambda x,y:x if y in x else x + [y]
                r_list = reduce(func,[[],]+r_list)
                return HttpResponse(json.dumps(r_list))

            if request.POST.get('check_type') == 'rollback_history_list':
                if request.POST.get('get_type') == 'panel-group':
                    grp = request.POST.get('tgt_select')
                    tgt_select = SaltGroup.objects.get(nickname=grp).groupname
                else:
                    tgt_select = request.POST.get('tgt_select')
                cur_path = request.POST.get('rollback_list', None)
                rollback_history_list = FileRollback.objects.filter(cur_path=cur_path).filter(target=tgt_select)
                for r in rollback_history_list:
                    r_list.append(r.bak_path)
                return HttpResponse(json.dumps(r_list))

            if request.POST.get('check_type') == 'rollback_history_remark':
                if request.POST.get('get_type') == 'panel-group':
                    grp = request.POST.get('tgt_select')
                    tgt_select = SaltGroup.objects.get(nickname=grp).groupname
                else:
                    tgt_select = request.POST.get('tgt_select')
                bak_path = request.POST.get('rollback_remark', None)
                rollback_history_remark = FileRollback.objects.filter(bak_path=bak_path).filter(target=tgt_select)
                for r in rollback_history_remark:
                    r_list.append(r.remark)

                return HttpResponse(json.dumps(r_list))

            else:
                if request.POST.get('check_type') == 'panel-group':
                    grp = request.POST.get('tgt_select')
                    tgt_select = SaltGroup.objects.get(nickname=grp).groupname
                    expr_form = 'nodegroup'
                else:
                    tgt_select = request.POST.get('tgt_select')
                    expr_form = 'list'
                remote_path = request.POST.get('remote_path')
                history_version = request.POST.get('history_version')
                sapi = SaltAPI(url=settings.SALT_API['url'],username=settings.SALT_API['user'],password=settings.SALT_API['password'])
                ret = sapi.file_copy(tgt_select, 'cp.get_file', history_version, remote_path, expr_form)
                rst = ''
                for k in ret:
                    rst = rst + u'主机：' + k + '\n回滚结果：\n' + ret[k] + '\n' + '-'*80 + '\n'

                Message.objects.create(type=u'文件管理', user=request.user, action=u'文件回滚', action_ip=UserIP(request),content=u'文件回滚 %s'%rst)

                return HttpResponse(json.dumps(rst))

@login_required
def salt_advanced_manage(request):
    ret = ''
    if request.method == 'POST':
        if request.is_ajax():
            tgt_selects = request.POST.getlist('tgt_select', None)
            args = request.POST.getlist('arg', None)
            checkgrp = request.POST.getlist('ifcheck', None)
            check_type = request.POST.get('check_type', None)
            if check_type == 'panel-group':
                expr_form = 'nodegroup'
            else:
                expr_form = 'list'
            s='::'.join(str(i) for i in checkgrp)
            checkgrp = s.replace('0::1','1').split('::')
            sapi = SaltAPI(url=settings.SALT_API['url'],username=settings.SALT_API['user'],password=settings.SALT_API['password'])
            for i in range(0,len(tgt_selects)):
                try:
                    jid = sapi.remote_execution(tgt_selects[i], 'cmd.run', args[i] + ';echo ":::"$?', expr_form)
                    if check_type == 'panel-group':
                        s = SaltGroup.objects.get(groupname=tgt_selects[i])
                        s_len = s.minions.all().count()
                    else:
                        s = tgt_selects[i].split(',')
                        s_len = len(s)
                    rst = {}
                    while(len(rst)<s_len):
                        rst = sapi.salt_runner(jid)
                        #time.sleep(1)
                    j = 0
                    for k in rst:
                        ret = ret + u'L%s-%s 主机：'%(i,j) + k + '\n运行结果：\n' + rst[k] + '\n'
                        j = j + 1
                        r = rst[k].split(':::')[-1].strip()
                        if r != '0':
                            ret = ret + '%s 执行失败！\nJobs NO. %s\n'%(args[i],jid) + '-'*80 + '\n'
                            if checkgrp[i] == '0':
                                try:
                                    Message.objects.create(type=u'部署管理', user=request.user, action=jid, action_ip=UserIP(request),content=u'高级管理 %s'%ret)
                                except:
                                    print 'Log Err'
                                return HttpResponse(json.dumps(ret))
                            else:
                                continue
                        else:
                            ret = ret + '%s 执行成功！\nJobs NO. %s\n'%(args[i],jid) + '-'*80 + '\n'
                except:
                    print 'Err'
            try:
                Message.objects.create(type=u'部署管理', user=request.user, action=jid, action_ip=UserIP(request),content=u'高级管理 %s'%ret)
            except:
                print 'Log Err'

            return HttpResponse(json.dumps(ret))

    return render(request, 'salt_remote_exec_advance.html', {'ret':ret})

@login_required
def salt_task_list(request):
    '''
    任务列表
    '''
    if request.method == 'GET':
        if request.GET.has_key('tid'):
            tid = request.get_full_path().split('=')[1]
            log_detail = Message.objects.filter(user=request.user).filter(id=tid).exclude(type=u'用户登录').exclude(type=u'用户退出')
            return render(request, 'salt_task_detail.html', {'log_detail':log_detail})

    logs = Message.objects.filter(user=request.user).exclude(type=u'用户登录').exclude(type=u'用户退出')[:200]

    return render(request, 'salt_task_list.html', {'all_logs':logs})

@login_required
def salt_task_check(request):
    '''
    任务查询
    '''
    if request.method == 'POST':
        if request.is_ajax():
            jid = request.POST.get('jid')
            check_type = request.POST.get('check_type')
            try:
                ret=AjaxResult(jid,check_type)
            except:
                print 'Err'
                pass
            return HttpResponse(json.dumps(ret))

    return render(request, 'salt_task_check.html', {})
