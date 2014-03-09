#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#  Copyright (C) 2014 konglx
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
#  1. Redistributions of source code must retain the above copyright
#  notice, this list of conditions and the following disclaimer.
#  2. Redistributions in binary form must reproduce the above copyright
#  notice, this list of conditions and the following disclaimer in the
#  documentation and/or other materials provided with the distribution.
#
#  THIS SOFTWARE IS PROVIDED BY konglx ''AS IS'' AND ANY
#  EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#  WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#  DISCLAIMED. IN NO EVENT SHALL konglx BE LIABLE FOR ANY
#  DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#  (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#   LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#  ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#
#  The views and conclusions contained in the software and documentation
#  are those of the authors and should not be interpreted as representing
#  official policies, either expressedor implied, of konglx.
#
#  File        : plugin_manager.py
#  Author      : konglx
#  Email       : jayklx@gmail.com
#  Date        : 2014-03-10
#  Description : plugin manager for tombot

import sys

from importlib import import_module
from threading import Thread
from inspect import isclass
import logging

from forwarder import config
from engine import Engine

logger = logging.getLogger('')


class PluginManager(object):
    def __init__(self, directory=None):
        self.directory = directory
        self.actives = {}

    def load_scripts(self, type_, push):
        '''载入插件
        '''
        # 插件需要一个push连接以推送消息到adapter
        scripts = None
        if type_ == 'plugin':
            scripts = config.plugins
        if type_ == 'ansible':
            scripts = config.ansibles
        for plugin in scripts:
            if type_ == 'plugin':
                sys.path.append('scripts')
            elif type_ == 'ansible':
                sys.path.append('../ansible/')
            else:
                logger.warn('invalid type')
                continue

            m = import_module(plugin)
            for item in dir(m):
                attr = getattr(m, item)
                # 载入所有继承了Engine的类
                if isclass(attr) and issubclass(attr, Engine):
                    # 如果是Engine本身，跳过
                    if attr == Engine:
                        continue
                    if hasattr(attr, 'run'):
                        _instance = attr()
                        self.actives[plugin] = _instance
                        logger.info('正在实例化脚本{0}的{1}类...'.format(plugin, attr.__name__))
                        try:
                                p = Thread(target=_instance.run, args=(push,))
                                p.daemon = False
                        except Exception as e:
                            logger.warn('脚本载入失败，错误信息：{0}'.format(e))
                            continue
                        p.start()
