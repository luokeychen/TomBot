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
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#
#  The views and conclusions contained in the software and documentation
#  are those of the authors and should not be interpreted as representing
#  official policies, either expressedor implied, of konglx.
#
#  File        : enging.py
#  Author      : konglx
#  Email       : jayklx@gmail.com
#  Date        : 2014-02-09
#  Description : engine for TomBot

import logging

import json

from utils import make_msg
import const

logger = logging.getLogger(__name__)

respond_handlers = {}


def plugin(cls):
    cls.__plugin__ = True
    return cls


class Message(object):
    '''包装消息，方便保存上下文

    :param message: 消息tuple
    :param socket: pull模式的zmq socket
    '''

    #retcode: 0 normal 101 warn 102 error 1001 null
    def __init__(self, message, socket):
        self.msg = message
        self.identity = message[0]
        self.content, self.id_, self.type_ = message[1:]
        self.socket = socket
        self.respond_map = {}

    def send(self, content, style=const.DEFAULT_STYLE, retcode=0):
        if len(content) > 4096:
            warn_msg = make_msg(1,
                                '消息过长，只显示部分内容'.encode('utf-8'),
                                self.id_, self.type_, const.WARNING_STYLE)

            self.socket.send_json(warn_msg)
            content = content[:4096]
        msg = make_msg(retcode, content, self.id_, self.type_, style)

        self.socket.send_multipart([self.identity,
                                    json.dumps(msg)])

        logging.info('推送消息到adapter: {0!r}'.format(msg))

    def ok(self, content):
        self.send(content, style=const.OK_STYLE, retcode=0)

    def info(self, content):
        self.send(content, style=const.INFO_STYLE)

    def warn(self, content):
        self.send(content, style=const.WARNING_STYLE, retcode=101)

    def error(self, content):
        self.send(content, style=const.ERROR_STYLE, retcode=102)

    def code(self, content):
        self.send(content, style=const.CODE_STYLE)


class Respond(object):
    '''
    插件应继承此类

    '''
    def __init__(self):
        self.respond_map = {}

    def register(self, pattern):
        '''消息响应装饰器

        :param pattern: pattern应是一个合法的正则表达式
        '''
        def wrapper(func, *args, **kwargs):
            self.respond_map[pattern] = func.__name__
            logger.debug('function dict:{0}'.format(func.__dict__))
            return func
        return wrapper

    def get_respond(self, pattern):
        func_name = self.respond_map.get(pattern, None)
        if func_name is None:
            logger.warn('未注册响应器:{0}'.format(pattern))
        else:
            return func_name
