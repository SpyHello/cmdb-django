# -*- coding: utf8 -*-
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from asset_info import MultipleCollect
from models import ServerAsset
from deploy.models import SaltHost

import StringIO
import xlwt
import json

# Create your views here.
def SheetWrite(sheet, row, serverasset, style):
    sheet.write(row,0, serverasset.hostname+'['+serverasset.nodename+']', style)
    sheet.write(row,1, serverasset.os, style)
    sheet.write(row,2, serverasset.kernel, style)
    sheet.write(row,3, serverasset.saltversion, style)
    sheet.write(row,4, serverasset.zmqversion, style)
    sheet.write(row,5, serverasset.shell, style)
    sheet.write(row,6, serverasset.locale.replace('<br />', '\n'), style)
    sheet.write(row,7, serverasset.selinux.replace('<br />', '\n'), style)
    sheet.write(row,8, serverasset.cpu_model, style)
    sheet.write(row,9, serverasset.cpu_nums, style)
    sheet.write(row,10, serverasset.memory, style)
    sheet.write(row,11, serverasset.disk.replace('<br />', '\n'), style)
    sheet.write(row,12, serverasset.network.replace('<br />', '\n'), style)
    sheet.write(row,13, serverasset.virtual, style)
    sheet.write(row,14, serverasset.sn, style)
    sheet.write(row,15, serverasset.manufacturer+' '+serverasset.productname, style)
    sheet.write(row,16, serverasset.idc, style)

@login_required
def get_server_asset_info(request):
    '''
    获取服务器资产信息
    '''
    ret = ''
    all_server = ServerAsset.objects.all()
    idc=['IDC01', 'IDC02']

    if request.method == 'GET':
        if request.GET.has_key('aid'):
            aid = request.get_full_path().split('=')[1]
            server_detail = ServerAsset.objects.filter(id=aid)
            return render(request, 'server_asset_info_detail.html', {'server_detail': server_detail})

        if request.GET.has_key('get_idc'):
            return HttpResponse(json.dumps(idc))

        if request.GET.has_key('action'):
            action = request.get_full_path().split('=')[1]
            if action == 'flush':
                q = SaltHost.objects.filter(alive=True)
                tgt_list = []
                [tgt_list.append(i.hostname) for i in q]
                ret = MultipleCollect(tgt_list)
                for i in ret:
                    try:
                        server_asset = get_object_or_404(ServerAsset, nodename=i['nodename'])
                        for j in i:
                            if i[j] != 'Nan':
                                setattr(server_asset, j, i[j])
                        server_asset.save()
                    except:
                        server_asset = ServerAsset()
                        for j in i:
                            setattr(server_asset, j, i[j])
                        server_asset.save()
                return redirect('server_info')
        if request.GET.has_key('export'):
            response = HttpResponse(content_type='application/vnd.ms-excel')
            response['Content-Disposition'] = 'attachment;filename=服务器资产信息.xls'
            wb = xlwt.Workbook(encoding = 'utf-8')
            sheet = wb.add_sheet(u'服务器资产信息')

            alignment = xlwt.Alignment()
            alignment.horz = xlwt.Alignment.HORZ_LEFT
            alignment.vert = xlwt.Alignment.VERT_CENTER
            style = xlwt.XFStyle()
            style.alignment = alignment
            style.alignment.wrap = 1
            #1st line
            row0 = [u'主机名',u'操作系统',u'内核',u'Salt版本',u'ZeroMQ版本','Shell','Locale','SELinux',u'CPU型号',u'CPU线程',u'内存',u'硬盘分区',u'网络接口',u'平台',u'序列号',u'厂商型号',u'IDC机房']
            for i in range(0, len(row0)):
                sheet.write(0,i,row0[i])
                sheet.col(i).width = 6666

            export = request.GET.get('export')
            id_list = request.GET.getlist('id')
            row = 1
            if export == 'check':
                for id in id_list:
                    serverasset = get_object_or_404(ServerAsset, pk=id)
                    SheetWrite(sheet, row, serverasset, style)
                    row = row + 1
            elif export == 'check_all':
                for serverasset in ServerAsset.objects.all():
                    SheetWrite(sheet, row, serverasset, style)
                    row = row + 1
            output = StringIO.StringIO()
            wb.save(output)
            output.seek(0)
            response.write(output.getvalue())
            return response
    if request.method == 'POST':
        field = request.POST.get('field')
        value = request.POST.get('value')
        if field == 'idc':
            value = idc[int(value)]
        value = str(value)
        id = request.POST.get('id')
        ServerAsset.objects.filter(id=id).update(**{field:value})
        return HttpResponse(value)

    return render(request, 'server_asset_info.html', {'all_server':all_server})

@login_required
def idc_info_json(request):
    idc=['IDC01', 'IDC02']
    return HttpResponse(json.dumps(idc))
