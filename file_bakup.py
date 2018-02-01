#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import shutil
import hashlib

def md5sum(fname):
    """ 计算文件的MD5值
    """
    def read_chunks(fh):
        fh.seek(0)
        chunk = fh.read(8096)
        while chunk:
            yield chunk
            chunk = fh.read(8096)
        else: #最后要将游标放回文件开头
            fh.seek(0)
    m = hashlib.md5()
    if isinstance(fname, basestring) \
            and os.path.exists(fname):
        with open(fname, "rb") as fh:
            for chunk in read_chunks(fh):
                m.update(chunk)
    #上传的文件缓存 或 已打开的文件流
    elif fname.__class__.__name__ in ["StringIO", "StringO"] \
            or isinstance(fname, file):
        for chunk in read_chunks(fname):
            m.update(chunk)
    else:
        return ""
    return m.hexdigest()

def Backup(dest, tag, md5):
    bkpath = os.path.join('/srv/salt', '%s-%s'%(dest.lstrip('/'),tag))
    if not os.path.isdir(os.path.dirname(bkpath)):
        os.makedirs(os.path.dirname(bkpath))
    try:
        md5_new = md5sum(dest)
        if md5_new == md5:
            return 1
        else:
            shutil.copyfile(dest, bkpath)
            return 0
    except:
        return None

def Rollback(dest, tag, md5):
    bkpath = os.path.join('/srv/salt', '%s-%s'%(dest.lstrip('/'), tag))
    shutil.copyfile(bkpath, dest)
    return 'ok'
