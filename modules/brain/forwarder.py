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
#  File        : forwarder.py
#  Author      : konglx
#  Email       : jayklx@gmail.com
#  Date        : 2014-02-09
#  Description : forwarder for TomBot

    
from __future__ import print_function

import re
import imp
import logging
import os
import sys

from inspect import isclass, getfile

import yaml
import zmq.green as zmq
import gevent
from multiprocessing import Process

_path = os.path.abspath(os.path.dirname(__file__))

import types
sys.modules['config'] = types.ModuleType('config')
import config

config_file = file('{0}/../../conf/config.yaml'.format(_path))

yaml_dict = yaml.load(config_file)
config.name = yaml_dict.get('name')
config.home = yaml_dict.get('home')
config.ipc_path = yaml_dict.get('ipc_path')
config.log_level = yaml_dict.get('log_level')
config.plugins = yaml_dict.get('plugins')
config.debug = yaml_dict.get('debug')
config.ansibles = yaml_dict.get('ansibles')

logger = logging.getLogger('')

def init_logger():
    '''初始化logger
    '''

    fmt = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)

    fh = logging.FileHandler('{0}/log/tom.log'.format(config.home))
    fh.setFormatter(fmt)

    logger.addHandler(fh)

    if config.log_level == 'debug':
        logger.setLevel(logging.DEBUG)
    elif config.log_level == 'info':
        logger.setLevel(logging.INFO)
    elif config.log_level == 'warn':
        logger.setLevel(logging.WARN)
    elif config.log_level == 'error':
        logger.setLevel(logging.ERROR)
    elif config.log_level == 'critical':
        logger.setLevel(logging.CRITICAL)
    else:
        logging.error('错误的日志级别，请设置成debug, info, warning, error, critical中的一个')


    if config.debug:
        logger.addHandler(ch)
        logger.setLevel(logging.DEBUG)
    return logger

def load_scripts():
    '''载入插件
    '''
    for plugin in config.plugins:
        m = imp.load_source(plugin, '{0}/scripts/{1}.py'.format(_path, plugin))
        for item in dir(m):
            attr = getattr(m, item)
            if isclass(attr) and plugin in getfile(attr):
                if hasattr(attr, 'run'):
                    _instance = attr()
                    logger.info('正在实例化脚本{0}的{1}类...'.format(plugin, attr.__name__))
                    try:
                            p = Process(target=_instance.run)
                    except AttributeError as e:
                        logger.warn('脚本载入失败，错误信息：{0}'.format(e))
                        continue
                    p.start()


def forwarding():
    '''
    转发函数，订阅消息，并把正确的消息过滤完后送给scripts
    '''
    name = config.name
    context = zmq.Context(1)
    frontend = context.socket(zmq.SUB)
    frontend.setsockopt(zmq.IDENTITY, 'Frontend')
    # 订阅以机器人名字开头的消息，包括小写、大写、首字母大写

    frontend.setsockopt(zmq.SUBSCRIBE, '@' + name)
    frontend.setsockopt(zmq.SUBSCRIBE, name.lower())
    frontend.setsockopt(zmq.SUBSCRIBE, name.upper())
    frontend.setsockopt(zmq.SUBSCRIBE, name.capitalize())
    frontend.bind('ipc://{0}/publish.ipc'.format(config.ipc_path))

    backend = context.socket(zmq.PUB)
    backend.setsockopt(zmq.IDENTITY, 'Backend')
    backend.bind('ipc://{0}/route.ipc'.format(config.ipc_path))
    # 把名字过滤掉，再转发给scripts，以便脚本正确的处理订阅字符串
    pattern = re.compile('^{0}'.format(name), flags=re.IGNORECASE)

    poller = zmq.Poller()
    poller.register(frontend, zmq.POLLIN)

    def _recv():
        while True:
            socks = dict(poller.poll())
            if frontend in socks and socks[frontend] == zmq.POLLIN:
                [_content, _id, _type] = frontend.recv_multipart()
                logging.debug('从adapter收到消息: {0}'.format((_content, _id, _type)))
                _content = pattern.sub('', _content, 1).strip()
                #这里暂时切出，避免socket异常
                gevent.sleep(0)
                backend.send_multipart([_content, _id, _type])
                logging.debug('发布消息给scripts: {0}'.format((_content, _id, _type)))

    gevent.spawn(_recv).join()

def run():
    init_logger()
    logger.info('开始载入脚本...')
    load_scripts()
    logger.info('脚本载入完成')
    # forwarding 必须在子进程中运行，否则ioloop会有问题
    p = Process(target=forwarding)
    p.start()
    logger.info('forwarder 开始监听')
    p.join()

if __name__ == '__main__':
    try:
        run()
    except KeyboardInterrupt:
        logging.shutdown()
        exit(0)
