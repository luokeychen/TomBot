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
#  File        : enging.py
#  Author      : konglx
#  Email       : jayklx@gmail.com
#  Date        : 2014-02-09
#  Description : engine for TomBot

import logging
import re

import inspect
import functools

import zmq
from zmq.eventloop import zmqstream
from forwarder import config


logger = logging.getLogger('')


def respond_handler(arg):
    '''消息响应装饰器

    :param arg: arg应是一个合法的正则表达式
    '''
    regexp = re.compile(arg, re.IGNORECASE)

    def wrapper(func):
        def __handler(*args, **kwargs):
            matches = re.match(regexp, args[1].content)
            if matches:
#                print('匹配到正则表达式: {0}'.format(matches.string))
                return func(args[0], args[1], matches)
            else:
                return None
        return __handler
    return wrapper


class Message(object):
    '''包装消息，方便保存上下文

    :param message: 消息tuple
    :param socket: pull模式的zmq socket
    '''
    def __init__(self, message, socket):
        self.msg = message
        self.content, self.id, self.type = message
        self.content = self.content
        self.socket = socket

    def send(self, content):
        length = len(content)
        if length > 4096:
            self.socket.send_multipart(['消息过长，只显示部分内容', self.id, self.type])
            content = content[:4096]
        self.socket.send_multipart([content, self.id, self.type])
        logging.debug('推送消息到adapter: {0}'.format((content, self.id, self.type)))


class Engine(object):
    '''
    插件应继承此类, 并定制topics

    '''

    topics = []

    def setup_respond_handlers(self):
        '''
        获得被respond_handler装饰的函数列表
        '''
        respond_handlers = []
        for _, handler in inspect.getmembers(self, callable):
            # FIXME 这里用装饰过的函数名来判断被装饰过的函数列表，所以自己定义的任何callable对象，不能命名为__handler
            if handler.__name__ == '__handler':
                if handler not in respond_handlers:
                    respond_handlers.append(handler)
            else:
                continue

        self.respond_handlers = respond_handlers
        logger.debug('respond handlers: {0}'.format(self.respond_handlers))

    def _recv(self, msg, socket=None):
        '''接收消息

        :param socket: 一个socket连接，pull模式
        '''
        [_content, _id, _type] = msg
        logger.debug('从router收到消息: {0}'.format((_content, _id, _type)))
        for handler in self.respond_handlers:
            try:
                handler(Message((_content.decode('utf-8'), _id, _type), socket))
            except Exception as e:
                logger.exception(e)

    def run(self, push):
        self.setup_respond_handlers()
        # context 必须在run方法里创建
        # http://lists.zeromq.org/pipermail/zeromq-dev/2013-November/023670.html
        context = zmq.Context(1)

        subscriber = context.socket(zmq.SUB)
        subscriber.connect('ipc://{0}/route.ipc'.format(config.ipc_path))

        for topic in self.topics:
            subscriber.setsockopt(zmq.SUBSCRIBE, topic)

        logger.info('{0}脚本开始监听'.format(self.__class__.__name__))
        stream = zmqstream.ZMQStream(subscriber)
        callback = functools.partial(self._recv, socket=push)
        stream.on_recv(callback)
