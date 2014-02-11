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
import threading

import zmq.green as zmq
import gevent

from forwarder import config

logger = logging.getLogger('')


def respond_handler(arg):
    '''消息响应装饰器

    :param arg: arg应是一个合法的正则表达式
    '''
    regexp = re.compile(arg, re.IGNORECASE)
    def _handler(func):
        def __handler(*args, **kwargs):
            matches = re.match(regexp, args[1].content.decode('utf-8'))
            if matches:
                print('匹配到正则表达式: {0}'.format(regexp.__str__()))
                return func(args[0], args[1], matches)
            else:
                return None
        return __handler
    return _handler


class Message(object):
    '''包装消息，方便保存上下文
    
    :param message: 消息tuple
    '''
    def __init__(self, message, socket):
        self.msg = message
        self.content, self.id, self.type = message
        self.content = self.content.decode('utf-8').encode('utf-8')
        self.socket = socket

    def send(self, content):
        self.socket.send_multipart([content, self.id, self.type])
        logging.debug('推送消息到adapter: {0}'.format((content, self.id, self.type)))

class Engine(object):
    '''
    插件应继承此类

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

    def _recv(self, socket):
        '''接收消息
        
        :param msg: 收到的消息，是个tuple
        '''
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)

        while True:
            socks = dict(poller.poll())
            if socket in socks and socks[socket] == zmq.POLLIN:
                [_content, _id, _type] = socket.recv_multipart()
                logger.debug('从router收到消息: {0}'.format((_content, _id, _type)))
                for handler in self.respond_handlers:
                    try:
                        gevent.spawn(handler, Message((_content, _id, _type), self.push))
                    except Exception as e:
                        logger.exception(e)

    def run(self):
        self.setup_respond_handlers()
        # context 必须在run方法里创建
        # http://lists.zeromq.org/pipermail/zeromq-dev/2013-November/023670.html
        context = zmq.Context()
        self.push = context.socket(zmq.PUSH)
        self.push.connect('ipc://{0}/push.ipc'.format(config.ipc_path))

        subscriber = context.socket(zmq.SUB)
        subscriber.connect('ipc://{0}/route.ipc'.format(config.ipc_path))

        for topic in self.topics:
            subscriber.setsockopt(zmq.SUBSCRIBE, topic)

        logger.info('{0}脚本开始监听'.format(self.__class__.__name__))
        gevent.spawn(self._recv, subscriber).join()
