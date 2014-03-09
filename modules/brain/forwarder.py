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
import logging
import os
import sys

import yaml
import zmq
from zmq.eventloop import zmqstream
from zmq.eventloop import ioloop
ioloop.install()

_path = os.path.abspath(os.path.dirname(__file__))

from manager import Room, RoomManager

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
config.subpub_socket = yaml_dict.get('subpub_socket')
config.pullpush_socket = yaml_dict.get('pullpush_socket')
config.use_tcp = yaml_dict.get('use_tcp')

config.use_proxy = yaml_dict.get('use_proxy')
config.proxy_host = yaml_dict.get('proxy_host')
config.proxy_port = yaml_dict.get('proxy_port')

logger = logging.getLogger('')


def init_logger():
    '''初始化logger
    '''
    import tornado.log
    from tornado.options import options

    if not config.debug:
        options.log_file_prefix = '{0}/log/tom.log'.format(config.home)
        options.log_file_max_size = 5 * 1024 * 1024
        options.log_file_num_backups = 5
        tornado.log.enable_pretty_logging(options)
    else:
        tornado.log.enable_pretty_logging()

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
    return logger


def forwarding():
    '''
    转发函数，订阅消息，并把正确的消息过滤完后送给scripts
    '''
    name = config.name
    context = zmq.Context(1)
    frontend = context.socket(zmq.SUB)
    #ZMQ 4.0 以上才支持
    # frontend.setsockopt(zmq.CURVE_SERVER)
    frontend.setsockopt(zmq.IDENTITY, 'Frontend')

    filters = [config.name, '@' + name, config.name.lower(), config.name.upper(),
               config.name.capitalize()]
    # 订阅以机器人名字开头的消息，包括小写、大写、首字母大写

    for _filter in filters:
        frontend.setsockopt(zmq.SUBSCRIBE, _filter)

    if config.use_tcp:
        frontend.bind(config.subpub_socket)
    else:
        frontend.bind('ipc://{0}/publish.ipc'.format(config.ipc_path))

    backend = context.socket(zmq.PUB)
    backend.setsockopt(zmq.IDENTITY, 'Backend')
    backend.bind('ipc://{0}/route.ipc'.format(config.ipc_path))
    # 把名字过滤掉，再转发给scripts，以便脚本正确的处理订阅字符串

    room_manager = RoomManager()

    def callback(msg):
        [_content, _id, _type] = msg

        #若该房间不在字典中，则添加一个
        if not room_manager.get_room(_id):
            room = Room(_id)
            room_manager.add_room(room)
        else:
            room = room_manager.get_room(_id)

        logging.debug('从adapter收到消息: {0}'.format((_content, _id, _type)))
        #模式切换特殊处理
        if _content.strip() == 'tom mode cmd':
            room.mode = 'command'
            logger.info('切换到command模式')
            frontend.setsockopt(zmq.SUBSCRIBE, '')
            backend.send_multipart([str('notify Tom已切换到command模式'), _id, _type])
            return
        if _content.strip() == 'tom mode normal':
            room.mode = 'normal'
            logger.info('切换到normal模式')
            #FIXME 这里似乎无法退订成功
            frontend.setsockopt(zmq.UNSUBSCRIBE, '')
            backend.send_multipart([str('notify Tom已切换到normal模式'), _id, _type])
            return

        #命令模式自动补exec让脚本能够正常处理
        if room.mode == 'command':
            #非英文开头直接忽略
            if re.compile('^[a-z]').match(_content):
                _content = 'exec ' + _content
            else:
                return
        else:
            #因为前面退订的bug，需要这么处理
            pattern = re.compile('^{0}'.format(config.name), flags=re.IGNORECASE)
            if pattern.match(_content):
                _content = pattern.sub('', _content, 1).strip()
            else:
                return
        backend.send_multipart([_content, _id, _type])
        logging.debug('发布消息给scripts: {0}'.format((_content, _id, _type)))

    stream = zmqstream.ZMQStream(frontend)
    stream.on_recv(callback)

    loop = ioloop.IOLoop.instance()
    try:
        loop.start()
    except KeyboardInterrupt:
        logger.info('收到退出信号，程序退出...')
        ioloop.IOLoop.instance().stop()
